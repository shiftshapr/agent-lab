# Bride of Charlie (Monument Zero)

First monument project. Uses the Episode Analysis Protocol for structured investigative records.

## Structure

- **brief/** — Project briefing (protocol rules)
- **templates/** — Output format for episode analyses
- **input/** — YouTube links (`youtube_links.txt`) or raw transcripts
- **transcripts/** — Fetched YouTube transcripts (with timestamps)
- **drafts/** — Episode inscriptions + cross-episode analysis (for review)
- **output/** — Approved inscriptions (after review)
- **protocol_updates/** — Change log with reasons
- **scripts/** — Workflow scripts
- **logs/** — Run logs

See **WORKFLOW.md** for the full process.

## Usage

1. Place episode transcripts in `input/`
2. Run from agent-lab root:

```bash
uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py --protocol episode_analysis --project bride_of_charlie
```

Or with env var:

```bash
EPISODE_ANALYSIS_PROJECT=bride_of_charlie uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py --protocol episode_analysis
```

## Ledger

Artifacts (A-), Claims (C-), and Nodes (N-) use a global cross-episode numbering ledger. Each new episode continues from the highest existing ID. Do not renumber.
