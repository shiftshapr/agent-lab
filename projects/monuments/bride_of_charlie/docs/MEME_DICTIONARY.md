# Canonical Meme Dictionary

Shared across monuments. Used for meme analysis in episode extraction.

---

## Structure

| Field | Description |
|-------|-------------|
| `canonical_term` | The standard term (like canonical_name for nodes) |
| `type` | `meme` \| `euphemism` \| `code` |
| `aliases` | Variants, spellings, or related phrases |
| `definition` | Brief definition or usage context |
| `context` | Monument or domain where it appears |

---

## Types

- **meme** — Recurring image, phrase, or concept used as cultural shorthand
- **euphemism** — Indirect or softened expression substituting for a blunt term
- **code** — Deliberately obscure term or phrase with specific meaning to insiders

---

## Usage

1. **Add entries** — `python scripts/canonical_memes.py add "term" --type meme --definition "..."`
2. **List** — `python scripts/canonical_memes.py list`
3. **Episode extraction** — Template includes meme analysis; LLM references M-N IDs from dictionary
4. **De-dup at ingestion** — Same as nodes: new terms get next M-ID; aliases merge into existing

---

## Occurrence Format (per episode)

Each meme reference records occurrences with:

| Field | Purpose |
|-------|---------|
| `episode` | Episode number |
| `video_timestamp` | When in video (HH:MM:SS) |
| `quote` | Exact or near-exact quote |
| `speaker_node_ref` | Who said it (NODE_1, NODE_2, etc.) |
| `context` | Surrounding context |
| `tags` | Optional (coded_language, political, etc.) |

See `docs/TAGS_AND_MEME_OCCURRENCES.md` for tag vocabularies.

---

## Integration

- Entity extraction template: `memes` array with structured occurrences
- Assign IDs from central counter (M-1, M-2, ...)
- Log edge cases for human review (e.g. "is X the same as M-3?")
