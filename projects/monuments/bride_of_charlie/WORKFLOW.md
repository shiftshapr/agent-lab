# Bride of Charlie Workflow

## Inputs

- **7 YouTube links** (episode URLs)

- **Transcript API key** (for fetching captions with timestamps)

---

## Process

### 1. Fetch transcripts

Agent fetches transcripts from YouTube (with timestamps) via transcript API.

**Output:** Raw transcripts stored in `input/` (or `transcripts/`)

---

### 2. Run protocol on episodes (in order)

Agent performs the Episode Analysis Protocol on each episode in sequence.

**Output:** Draft episode inscriptions in `drafts/` for review

---

### 3. Review episode inscriptions

Human reviews drafts. Agent notes any changes and reasons, updates protocol.

**Output:** `protocol_updates/` — change log with reasons

---

### 4. Cross-episode analysis

Agent performs cross-episode analysis across all processed episodes.

**Output:** Draft cross-episode results in `drafts/` for review

---

### 5. Review cross-episode results

Human reviews. Agent notes any changes and reasons, updates protocol.

**Output:** `protocol_updates/` — change log with reasons

---

### 6. Standby for future episodes

Workflow pauses. Ready for new episodes when available.

---

## Directory Structure

```
bride_of_charlie/
├── input/
│   └── youtube_links.txt   # 5 YouTube URLs (one per line)
├── transcripts/            # Fetched transcripts (with timestamps)
├── drafts/                 # Episode inscriptions + cross-episode results (awaiting review)
├── output/                 # Approved inscriptions (after review)
├── protocol_updates/       # Change log: changes, reasons, protocol updates
├── brief/
├── templates/
├── scripts/
│   ├── fetch_transcripts.py
│   ├── run_workflow.py
│   └── cross_episode_analysis.py
└── logs/
```

## Run Commands

From `~/workspace/agent-lab`:

1. Add YouTube links to `input/youtube_links.txt`
2. Set `TRANSCRIPT_API_KEY` in env if your transcript service requires it (youtube-transcript-api works for public captions without a key)
3. Run full workflow:

```bash
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py all
```

Or step by step:

```bash
# Step 1: Fetch transcripts
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py fetch

# Step 2: Run protocol on episodes -> drafts/
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes

# Re-run episodes when drafts are wrong or incomplete (e.g. from placeholder transcripts):
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force

# Step 3: Cross-episode analysis -> drafts/
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py cross
```

4. Review `drafts/`, log changes in `protocol_updates/`
5. Standby for future episodes
