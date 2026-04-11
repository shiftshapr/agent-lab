# Transcript QA: what worked, what hurt, how to improve (curator workflow)

This note captures a **high-cost manual pass** (order of **half a day** of curator time) on *Bride of Charlie* transcripts and downstream artifacts. Use it to improve **workflow, UX, and accuracy** so the next pass is shorter and fewer errors propagate into analysis.

---

## 1. What we did (outcomes)

- **Canonical text:** `transcripts_corrected/` is the editorial source of truth for episode text used in re-analysis.
- **Known STT failure modes removed or normalized:**
  - Repeated hallucinated clause tied to “Elizabeth Lane” / Putin (removed from corrected earlier; swept **inscription**, **raw** where needed, **JSON** snippets, **drafts**, **HTML review** `impl` text + refreshed `data-orig-b64` where applicable).
  - **`Charlie Kirk and Turning Point`** expanded where raw showed plain **Charlie Kirk** (corrected had drifted longer than raw in several places).
  - **`DuPant` → `DuPont`** in downstream files; **`Dupants` / family joke** left context-dependent.
- **Mechanical integrity:** fixed **non‑monotonic timestamps** (ep2 school block; ep4 reader-mail block remapped to sit before `[57:50]`), removed **duplicate caption line** (ep1 `[49:49]`), aligned **ep3** and **ep6** line splits to curator preference, fixed **“They should They should”** (ep4).
- **Removed workflow clutter from corrected:** `[verify audio: …]` markers stripped so analysis ingests clean dialogue lines only.
- **Tooling added:** `scripts/report_transcript_raw_vs_corrected_deltas.py` — compares **raw vs corrected** by **timestamp key** (joins lines that share the same clock), reports **large length deltas** and **timestamps only in one side** (useful after ad stripping).
- **Hashes:** `scripts/sync_transcript_hashes.py` run after substantive corrected edits so **inscription / phase1** JSON hashes stay aligned where wired.

---

## 2. What successfully identified problems (keep doing this)

| Technique | Why it worked |
|-----------|----------------|
| **Repo-wide grep** for absurd repeated phrases (Putin, CK+TP boilerplate) | Hallucinations are **verbatim repeats** across files; fast to find **fan-out** into JSON/HTML/inscription. |
| **Compare `transcripts/` vs `transcripts_corrected/`** | Surfaced **corrected longer than raw** (wrong direction for “fixing” STT) and **split vs merge** choices (e.g. horse racing, Lane block). |
| **Monotonic time scan** on corrected | Caught **clock going backwards** (impossible in a single linear listen) — often **digit** or **block paste** errors. |
| **Reading “does this parse?”** (grammar, duplicate words) | Caught **Candace Owens** line break, **They should** stutter, **Turning Point by Turning Point USA**. |
| **Tracing artifact lineage** | Explained *why* JSON still had Putin: **analysis / inscription / HTML** were generated from **stale** layers, not from corrected-only. |

---

## 3. Root causes (why the day was long)

1. **Multiple surfaces of truth** — `transcripts/`, `transcripts_corrected/`, `inscription/*`, `phase1_output/`, `output/`, `drafts/`, `reports/*.html` could disagree; fixing corrected **did not** automatically refresh everything.
2. **STT produces plausible garbage** — especially **name-adjacent** boilerplate; overrides alone do not catch novel hallucinations.
3. **“Corrected” drift** — sometimes corrected kept **longer** phrasing than raw; without diff discipline, **bad STT** could live in “corrected” until a human notices.
4. **Large HTML review artifact** — easy for **impl** column / base64 to hold old text unless **regenerated or batch-patched**.

---

## 4. Recommendations: workflow & UX (for humans)

**Single pipeline**

- Treat **`transcripts_corrected/`** as the **only** ingest for: episode analysis, snippet extraction, inscription rebuild, and review HTML regeneration.
- Add a **make / npm / python** target: `curate:freeze` = strip markers + `sync_transcript_hashes` + copy corrected → inscription transcript paths (if policy is mirror).

**Gate before analysis**

- **Lint transcripts** (fail CI or warn): blocklist strings (Putin clause, `DuPant`, optional `Charlie Kirk and Turning Point` allowlist by episode), **empty bodies**, **timestamp regression**, **duplicate consecutive bodies**.
- Run **`report_transcript_raw_vs_corrected_deltas.py`** with a threshold (e.g. 60) and save output under `reports/` for the curator to skim.

**UX for curator (reduce half-day repeats)**

- **One diff view** per episode: corrected vs raw with **timestamps aligned**, highlighting **length delta** and **only-in-raw** ad blocks (collapsed by default).
- **Deep links** in transcript lines (optional, or separate sheet): YouTube `watch?v=…&t=…s` generated from episode id + line time — curator jumps in **seconds**.
- **“Fan-out” checklist** after edits: auto-print which derived files are **older than** `transcripts_corrected/` mtime.

**Policy**

- Decide: are **`[verify audio: …]`** (or similar) allowed in a **sidecar** file (e.g. `transcripts_notes.yaml`) so corrected stays clean but provenance is preserved?

---

## 5. Open questions for the next agent

1. **Inscription / verbatim policy:** Should `inscription/*_transcript*.txt` always be **byte-identical** to corrected, or keep verbatim STT for forensics? If both, **naming** and **generation order** must be explicit.
2. **HTML review report:** Is `transcript_raw_vs_corrected_review.html` **generated** from a script in-repo, or hand-maintained? If generated, **wire the generator** into workflow; if hand-maintained, **stop** or add checksum test.
3. **Blocklist maintenance:** Should `config/transcript_suspicious_patterns.json` drive **CI** + **pre-commit**, and how do we avoid false positives on legitimate “Turning Point” mentions?
4. **Episode 1 `[49:46]` vs raw `[49:45]`/`[49:47]`:** Delta script reports “only in corrected” for **timestamp alignment** after ad removal — do we **normalize** timestamps toward raw for machine diff, or accept and **document**?
5. **Re-analysis:** After freezing corrected, does **`episode_analysis_protocol.py`** always prefer corrected paths (and log source), and are **drafts** regenerated so **transcript_snippet** cannot point at old text?
6. **Large repo commits:** Is **2.9MB** HTML acceptable in git long-term, or should reports live in **LFS** / CI artifacts?

---

## 6. File / tool quick reference

| Path | Role |
|------|------|
| `transcripts_corrected/episode_*.txt` | Curator canonical dialogue |
| `transcripts/episode_*.txt` | Raw STT reference |
| `scripts/report_transcript_raw_vs_corrected_deltas.py` | Timestamp-grouped raw vs corrected length report |
| `scripts/sync_transcript_hashes.py` | Hash sync for inscription / phase1 when present |
| `scripts/sync_corrected_long_lines_from_raw.py` | Heuristic: shorten corrected when much longer than raw (same line index; **ep1 special**) |
| `config/transcript_suspicious_patterns.json` | Seeds for lint / hints |
| `reports/transcript_raw_vs_corrected_review.html` | Human diff UI (keep in sync with policy above) |

---

## 7. Success metric for “next time”

- Curator spends **under one hour** per batch after first episode setup: **lint green**, **delta report** reviewed, **one** regen of derived artifacts, **no** grep hits on known blocklist after push.

---

*Last updated from the transcript QA session that produced this document (April 2026).*
