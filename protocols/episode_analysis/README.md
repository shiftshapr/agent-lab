# Episode Analysis Protocol

Reusable protocol for Bridge of Charlie and related projects. Processes episode transcripts into structured analysis using project briefs and templates.

## Structure

```
episode_analysis/
├── input/          # Raw episode transcripts (.txt, .md)
├── output/         # Structured episode analyses
├── briefings/      # Project briefs (context for analysis)
├── templates/      # Output format templates
└── logs/           # Run logs
```

## Projects

| Project | Briefing | Template |
|---------|----------|----------|
| Bridge of Charlie | `briefings/monument_zero_project_brief.md` | `templates/bridge_of_charlie_episode_analysis_template.md` |
| (add more) | | |

## Usage

1. Place project brief in `briefings/`
2. Place episode analysis template in `templates/`
3. Put episode transcripts in `input/`
4. Run: `python agents/protocol/protocol_agent.py --protocol episode_analysis`

## Adding Your Files

Copy or paste content from:

- `bride_of_charlie_episode_analysis_template.md` → `templates/bridge_of_charlie_episode_analysis_template.md`
- `monument_zero_project_brief.md` → `briefings/monument_zero_project_brief.md`
- Protocol instructions → see `ep_protocol_v1.md` and `episode_analysis_protocol.py`
