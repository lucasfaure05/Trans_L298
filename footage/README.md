# footage/

Drop raw takes here (any format `ffmpeg` reads: `.mp4`, `.mov`, `.mkv`, ...).

Then, in a terminal at the repo root (or with a fresh Claude Code session on
this repo), just say what you want, e.g.:

> edit these into a launch video

video-use will inventory the sources, propose a cut strategy, wait for your
OK, then write everything to `footage/edit/` - transcripts, the EDL, graded
clips, subtitles, and the final render (`footage/edit/final.mp4`). This
folder's raw files are never modified in place.

Files placed here (and everything under `edit/`) are git-ignored - they're
your local working media, not project source.
