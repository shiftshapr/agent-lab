---
name: youtube-transcript-to-disk
description: >-
  Fetches a YouTube transcript via TranscriptAPI, writes `.txt` and `.json` under
  `data/transcripts/youtube/`, and never assumes a default video. Use when the user
  wants a YouTube transcript saved to disk, TranscriptAPI transcript export, or to
  avoid losing transcript output in the terminal. Requires an explicit URL or video id
  every time.
---

# YouTube transcript → disk (TranscriptAPI)

## Rules (non-negotiable)

1. **Never pick a default YouTube video.** Do not run the fetch script without the user (or message) supplying a **specific** `watch` / `youtu.be` URL or **11-character video id**. If the target is missing, **stop** and ask for it — do not invent or reuse an example id.
2. **Each successful run charges TranscriptAPI.** Do not re-fetch the same video unless the user explicitly asks (e.g. refresh, captions updated). If `data/transcripts/youtube/<video_id>.txt` already exists, mention it and confirm before calling the API again.
3. **Prefer `--quiet`** so the full transcript is not dumped to stdout; output paths are printed on stderr. Use non-quiet only if the user wants to see the text in the terminal.

## Prerequisites

- Working directory: **agent-lab repo root** (`workspace/agent-lab`).
- Credentials in **`agent-lab/.env`**: `TRANSCRIPT_API_KEY` or `API_KEY` (TranscriptAPI bearer token). The script loads `.env` automatically.

## Command

```bash
cd /path/to/agent-lab
node scripts/fetch-transcriptapi-transcript.mjs --quiet "<YOUTUBE_URL_OR_11_CHAR_ID>"
```

Examples (user-supplied targets only):

```bash
node scripts/fetch-transcriptapi-transcript.mjs --quiet "https://www.youtube.com/watch?v=VIDEO_ID"
node scripts/fetch-transcriptapi-transcript.mjs --quiet "https://youtu.be/VIDEO_ID"
node scripts/fetch-transcriptapi-transcript.mjs --quiet VIDEO_ID
```

## Outputs (always written on success)

| File | Contents |
|------|----------|
| `data/transcripts/youtube/<video_id>.txt` | Lines `[HH:MM:SS] text` |
| `data/transcripts/youtube/<video_id>.json` | Raw `transcript` array + `video_url`, `fetched_at`, `line_count` |

Paths are under the agent-lab repo; `data/transcripts/youtube/` is intended to be commit-friendly (unlike `logs/`).

## Errors

- **HTTP 404** — API has no transcript for that video (often captions unavailable).
- **HTTP 408** — Transient; safe to retry with the **same** URL after a short wait (still one credit per successful attempt; do not spam retries).

## Related

- Bride pipeline uses Python `projects/monuments/bride_of_charlie/scripts/fetch_transcripts.py` (TranscriptAPI **or** `youtube-transcript-api`). This skill is for **explicit TranscriptAPI + guaranteed disk writes** via `scripts/fetch-transcriptapi-transcript.mjs`.
