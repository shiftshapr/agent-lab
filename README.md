# Agent Lab

Structured workflows for investigative analysis, protocols, and monument projects.

## Structure

- **agents/** — Protocol agent, drafting, publishing, etc.
- **protocols/** — Episode analysis, transcript protocols
- **projects/monuments/** — Bride of Charlie and other monument projects
- **framework/deer-flow/** — DeerFlow framework (clone separately if needed)

## Bride of Charlie Workflow

1. Add YouTube links to `projects/monuments/bride_of_charlie/input/youtube_links.txt`
2. Run: `uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py [fetch|episodes|cross|all]`
3. Review `drafts/`, log changes in `protocol_updates/`

## Environment

Copy `.env.example` to `.env` and set:
- `TRANSCRIPT_API_KEY` — for YouTube transcript fetching
- `MINIMAX_API_KEY` — for faster episode analysis (optional; falls back to Ollama)
