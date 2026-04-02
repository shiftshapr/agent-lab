---
name: work-log-ingestion
description: >-
  Turns Draft Editor work-log entries marked ingest=true into durable knowledge: append
  to a digest markdown file and re-run meta-layer graph ingest. Use for weekly sweeps,
  habit capture follow-up, or when the user says to process the work log / ingest links
  from the calendar.
---

# Work log → knowledge ingestion

## Source of truth

- **File**: `data/master_calendar.json` → array **`work_log`**
- **UI**: Draft Editor → **Calendar** tab → Work log (or **POST /api/work-log** with `ingest: true`)

Entries may include **`text`**, **`status`** (`started` / `finished` / `note`), **`attachments`** (URLs or paths), **`ingest`** (boolean; default true on create).

## When to use

- User: “Process the work log” / “Ingest this week’s work log” / “Sweep work_log for ingestion”
- Standing habit: **weekly** (e.g. Monday) run a sweep after dictation habit
- After a burst of **links_or_paths** captures

## Workflow

### 1. Sweep digest (idempotent)

From agent-lab root:

```bash
uv run python scripts/sweep-work-log-ingest.py
```

This script:

- Reads `work_log` from `data/master_calendar.json`
- Skips entries with `ingest: false`
- Skips entries already present in `knowledge/work_log_digest.md` (matched by `<!-- wl-id:{id} -->` markers)
- Appends new sections under `##` headings so **ingest-meta-layer-knowledge** can chunk them

### 2. Graph ingest

After the sweep, load chunks into Neo4j (same pipeline as other knowledge markdown):

```bash
uv run --project framework/deer-flow/backend python scripts/ingest-meta-layer-knowledge.py --file knowledge/work_log_digest.md
```

If the digest is new or large, a full knowledge run also picks it up when listed in the script’s default file set (see **ingest-meta-layer-knowledge.py**).

### 3. Optional agent steps (no script)

- Summarize high-value **`finished`** entries into **JAUmemory** `remember` (decisions, patterns).
- For **URLs** in attachments, fetch/summarize and use **add-to-meta-layer-graph** / user’s graph tools when appropriate.

## Rules

- **Do not** re-append the same work-log `id`—the sweep script guards with HTML comments.
- **Secrets**: Never paste tokens or private URLs into the digest; redact if needed.
- Prefer **sweep script + ingest** for bulk; use **manual graph add** for one-off gold nuggets.

## Related

- **master-calendar** skill — API and calendar semantics
- **ingest-meta-layer-knowledge.py** — Neo4j chunks for RAG
