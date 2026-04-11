# Episode audio from video (workflow plan)

The Draft Editor **Listen** control prefers **local** files under `input/audio/episode_NNN.*` (see `GET /api/bride/episode/<n>/audio`). If those files are missing, it falls back to an embedded YouTube player.

This document is the plan to **derive that audio from the same video URLs** you already use for transcripts (`input/youtube_links.txt`, line order = episode 1…N).

## Goal

- One audio file per episode, on disk, next to the monument.
- Same episode index as `youtube_links.txt` and `inscription/episode_NNN_transcript.txt`.
- No manual export step in the browser; **batch** from the command line (or CI).

## Recommended tool

**[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — actively maintained fork of youtube-dl, extracts **audio only** (`-x`) into `.m4a` / `.mp3` without keeping full video on disk (unless you choose otherwise).

Install (pick one):

- `brew install yt-dlp` (macOS)
- `pip install yt-dlp` (then use `python3 -m yt_dlp` or ensure the `yt-dlp` script is on `PATH`)

Optional: `ffmpeg` on PATH (yt-dlp uses it for merge/remux on some formats).

## Automation in this repo

Script: **`scripts/fetch_episode_audio_from_youtube.py`**

```bash
cd projects/monuments/bride_of_charlie

# All episodes (skips episodes that already have a file unless --force)
python3 scripts/fetch_episode_audio_from_youtube.py

# One episode
python3 scripts/fetch_episode_audio_from_youtube.py --episode 3

# See commands without running
python3 scripts/fetch_episode_audio_from_youtube.py --dry-run
```

Outputs under **`input/audio/`** as `episode_001.m4a`, `episode_002.m4a`, … (same stem the Draft Editor looks for).

## Where it fits in the pipeline

Suggested order (conceptual):

1. **Stable `input/youtube_links.txt`** — one URL per episode in order.
2. **Fetch transcripts** — existing `scripts/fetch_transcripts.py` (or your TranscriptAPI path).
3. **`fetch_episode_audio_from_youtube.py`** — pull audio once per episode (or refresh with `--force` when a video is re-uploaded).
4. **Inscription / overrides / Draft Editor** — verify with **Listen** using local audio when present.

You can run step 3 **after** links exist; re-run when URLs change. It does **not** need to run on every editorial pass.

## CI / server

- Run on a machine that has **`BRIDE_PROJECT_ROOT`** (or the repo checkout) and **`yt-dlp`**.
- YouTube may rate-limit or require cookies for some content; keep runs **sequential** or low parallelism for reliability.
- Store **`input/audio/`** in git only if policy allows (large binaries); otherwise **artifact** or **object storage** and sync before Draft Editor.

## Policy and responsibility

Downloading or extracting streams may be restricted by **YouTube’s Terms of Service** and by **copyright**. Use this only for **content you have rights to** (e.g. your own channel, licensed material, or internal review copies). This tooling is for **local review** aligned with your transcript workflow—not a recommendation to bypass platform rules.

## Future hooks (optional)

- Wire **`fetch_episode_audio_from_youtube.py`** into `run_full_workflow.py` behind **`BRIDE_FETCH_EPISODE_AUDIO=1`** once stable.
- Add a **Draft Editor** button “Download episode audio” that shells to the same script (server-side only; requires `yt-dlp` on the host).
