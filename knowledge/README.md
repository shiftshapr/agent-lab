# Knowledge Base — shapes Shiftshapr and subagents

Content here is loaded into Shiftshapr's context. Add summaries, key excerpts, or full text.

## Structure

| File | Purpose |
|------|---------|
| `metaweb_book.md` | Metaweb book — key concepts, frameworks, your thinking |
| `substack_highlights.md` | Curated summary of Substack articles (themes, arguments, examples) |
| `canvas_insights.md` | Exported insights from ChatGPT canvases |
| `docs/` | Documents — markdown (book chapters, papers). Use `scripts/ingest-pdf.py` to extract PDFs to `.md` here |
| `docs/*.md` (Metaweb book) | Generated from `docs/*.htm` via `uv run python scripts/convert-metaweb-htm-to-md.py`. Each file has `# Title` then `**On-chain:** https://ordinals.com/content/<id>`. Per-chapter ids come from `docs/metaweb_inscriptions.csv` (columns `inscriptionId`, `address`, `filename`) when present; otherwise the script falls back to the first `/content/...` id in the HTML. |

## How to add content

1. **Metaweb book** — Edit `metaweb_book.md`: paste key excerpts, chapter summaries, or a distilled outline
2. **Substack** — Edit `substack_highlights.md`: export posts to markdown, or write a highlights doc with themes + representative quotes. Or use [Substack export](https://support.substack.com/hc/en-us/articles/360037581273-Export-your-newsletter) and add key posts.
3. **ChatGPT canvases** — Copy/paste to `canvas_insights.md`, or create `knowledge/canvas_foo.md` and add to knowledge_sources
4. **Documents** — Run `python scripts/ingest-pdf.py path/to/file.pdf` → creates `knowledge/docs/filename.md`. Or place markdown (e.g. book chapters) directly in `knowledge/docs/`. Add `docs/filename.md` to knowledge_sources in shiftshapr_context.json

## Config

In `data/shiftshapr_context.json`:

```json
"knowledge_sources": ["metaweb_book.md", "substack_highlights.md", "canvas_insights.md"]
```

Or use `"knowledge_sources": ["*"]` to load all `.md` files in `knowledge/`.

## Graph RAG (Neo4j)

Knowledge can be stored in Neo4j for scalable retrieval. When Neo4j has content, Shiftshapr uses graph RAG instead of loading files — retrieves relevant chunks by query keywords. The graph also supports **opportunities** and **drafting** — concepts and frameworks inform how Shiftshapr identifies and tracks opportunities and drafts content.

1. **Ingest** — `uv run --project framework/deer-flow/backend python scripts/ingest-meta-layer-knowledge.py [--force]`
2. **Enrich** — `uv run --project framework/deer-flow/backend python scripts/enrich-meta-layer-graph.py --file knowledge/urls/foo.md` — extracts orgs, reports, concepts, entities, opportunities
3. **Add via chat** — URL + "add to my graph" or PDF + caption "add to my graph" → ingest + enrich automatically
4. **Schema** — See `knowledge/meta_layer_schema.md`

Node types: MLPrimitive, MLConcept, MLFramework, MLSource, MLChunk. Same Neo4j as Bride of Charlie; ML* nodes are separate.

## Token limits (file fallback)

When graph is empty, knowledge loads from files. Default: ~16k chars total. Edit `KNOWLEDGE_MAX_CHARS` in shiftshapr if needed.
