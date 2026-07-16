# Video editing studio

This repo is a conversation-driven video editing studio, powered by two
open-source Claude Code skills:

- **video-use** (https://github.com/browser-use/video-use) - drop raw
  footage in `footage/`, chat with Claude Code, get `footage/edit/final.mp4`
  back. Transcribes with word-level timestamps, cuts filler words and dead
  air, color grades, burns subtitles, adds 30ms audio fades at every cut,
  and self-evaluates the render before showing it to you.
- **HyperFrames** (https://github.com/heygen-com/hyperframes) - renders
  animation overlays (lower-thirds, kinetic captions, data callouts, motion
  graphics, full HTML-native compositions) that video-use spawns in
  parallel sub-agents while cutting your footage. Also usable standalone
  for product-launch videos, PR walkthroughs, slideshows, and more.

Both ship as Claude Code skills and are vendored into this repo so they're
available in every session - no manual install step.

## Layout

- `.claude/skills/` - symlinks Claude Code reads (points into `.agents/skills/`)
- `.agents/skills/` - canonical skill sources (video-use, hyperframes-*, ...)
- `agent/skills/` - duplicate copies in "universal" layout for other agents
  (Codex, Cursor, etc.) - kept in sync by the hyperframes `skills add`
  installer, not hand-edited
- `footage/` - drop your raw takes here; outputs land in `footage/edit/`

## One-time setup

1. **ffmpeg** - required by video-use, installed automatically by the
   session-start hook (`.claude/hooks/session-start.sh`) in Claude Code on
   the web. Locally: `brew install ffmpeg` (macOS) or
   `sudo apt install ffmpeg` (Debian/Ubuntu) or download a build for Windows.
2. **OpenAI API key** - required for transcription (Whisper). Copy
   `.env.example` to `.env` and paste your key from
   https://platform.openai.com/api-keys. Never commit `.env`. Note: no
   speaker diarization or audio-event tagging (those are ElevenLabs
   Scribe-only features) - best for single-speaker footage. Uploads are
   capped at 25MB (~50 min at the 64kbps mono mp3 this project extracts).
3. **Node.js 22+** - required by HyperFrames (invoked via `npx hyperframes`,
   no global install needed).

## Usage

Drop footage into `footage/`, then in a Claude Code session on this repo:

> edit these into a launch video

For an animation-only ask (no footage, e.g. a product teaser or a PR
walkthrough), start with:

> Using /hyperframes, create a 30-second product launch video for <url/brief>

See `footage/README.md` for the video-use flow and
`.agents/skills/hyperframes/SKILL.md` for the full HyperFrames skill router.

## Keeping skills up to date

- video-use: `.agents/skills/video-use` is a vendored copy of the upstream
  repo. Re-sync by re-cloning `browser-use/video-use` and copying its
  contents over `.agents/skills/video-use` (and `agent/skills/video-use`).
- HyperFrames: `npx skills add heygen-com/hyperframes --all --full-depth --yes`
  from the repo root re-installs/updates all 19 skills in place.
