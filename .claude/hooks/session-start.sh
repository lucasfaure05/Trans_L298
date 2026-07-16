#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

# ffmpeg/ffprobe are hard requirements for video-use.
if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ffmpeg >/dev/null
fi

# Python deps for the video-use helpers/ scripts (transcribe, render, grade, timeline_view).
if command -v pip >/dev/null 2>&1; then
  pip install --quiet --disable-pip-version-check requests librosa matplotlib pillow numpy
fi
