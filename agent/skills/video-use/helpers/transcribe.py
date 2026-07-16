"""Transcribe a video with the OpenAI transcription API (Whisper).

Extracts mono 16kHz audio via ffmpeg, uploads to OpenAI with word-level
timestamps, writes the full response to <edit_dir>/transcripts/<video_stem>.json.

Note: OpenAI has no speaker diarization and no audio-event tagging
((laughter), (applause), ...) -- those are ElevenLabs Scribe features this
project no longer uses. Every word comes back with speaker_id=None; only
'word' and 'spacing' entries are ever produced, never 'audio_event'.

Also note: OpenAI's endpoint caps uploads at 25MB. Audio is extracted as
64kbps mono mp3 to fit long takes in that budget (~50 min); anything longer
will fail with a clear error asking you to split the source first.

Cached: if the output file already exists, the upload is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language en
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests


OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL = "whisper-1"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def load_api_key() -> str:
    for candidate in [Path(__file__).resolve().parent.parent / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "OPENAI_API_KEY":
                    return v.strip().strip('"').strip("'")
    v = os.environ.get("OPENAI_API_KEY", "")
    if not v:
        sys.exit("OPENAI_API_KEY not found in .env or environment")
    return v


def extract_audio(video_path: Path, dest: Path) -> None:
    """Extract mono 16kHz 64kbps mp3 -- small enough for many takes to fit
    under OpenAI's 25MB upload cap while staying plenty clear for ASR."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def call_openai(
    audio_path: Path,
    api_key: str,
    language: str | None = None,
) -> dict:
    size = audio_path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        mb = size / (1024 * 1024)
        raise RuntimeError(
            f"audio is {mb:.1f}MB, over OpenAI's 25MB upload cap. "
            "Split the source video into shorter takes and re-transcribe each."
        )

    data: dict[str, str] = {
        "model": OPENAI_MODEL,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
    }
    if language:
        data["language"] = language

    with open(audio_path, "rb") as f:
        resp = requests.post(
            OPENAI_TRANSCRIPTIONS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (audio_path.name, f, "audio/mpeg")},
            data=data,
            timeout=1800,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI returned {resp.status_code}: {resp.text[:500]}")

    return resp.json()


def to_scribe_shape(openai_payload: dict) -> dict:
    """Convert OpenAI's {word, start, end} list into the word/spacing shape
    the rest of video-use (pack_transcripts.py, timeline_view.py) expects.
    speaker_id is always None; 'audio_event' entries never occur.
    """
    words: list[dict] = []
    prev_end: float | None = None
    for w in openai_payload.get("words", []):
        start = w.get("start")
        end = w.get("end")
        if start is None or end is None:
            continue
        if prev_end is not None and start > prev_end:
            words.append({"type": "spacing", "start": prev_end, "end": start})
        words.append({
            "type": "word",
            "text": w.get("word", ""),
            "start": start,
            "end": end,
            "speaker_id": None,
        })
        prev_end = end
    return {
        "words": words,
        "language": openai_payload.get("language"),
        "duration": openai_payload.get("duration"),
        "text": openai_payload.get("text"),
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    api_key: str,
    language: str | None = None,
    num_speakers: int | None = None,  # kept for call-site compatibility; unused (no diarization)
    verbose: bool = True,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Cached: returns existing path immediately if the transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.mp3"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  uploading {video.stem}.mp3 ({size_mb:.1f} MB)", flush=True)
        raw = call_openai(audio, api_key, language)
        payload = to_scribe_shape(raw)

    out_path.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {len([w for w in payload['words'] if w['type'] == 'word'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video with the OpenAI transcription API")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code (e.g., 'en'). Omit to auto-detect.",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    api_key = load_api_key()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        api_key=api_key,
        language=args.language,
    )


if __name__ == "__main__":
    main()
