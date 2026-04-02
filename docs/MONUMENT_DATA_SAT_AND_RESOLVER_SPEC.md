# Monument data sat, off-chain index, and resolver (internal spec)

**Status:** internal draft — monument keeper + indexer implementers.  
**Scope:** Ordinals inscriptions for monument entries, a shared (or per-monument) **data sat** for registry and text-level directives, and an **off-chain index** that must always be read **together** with on-chain data.

---

## 1. Goals

- **Entry content** on each monument’s **entry sat** stays the primary bulk artifact (JSON and related layers). Immutability of past inscriptions is preserved.
- **Lineage** across sat sales: if an entry sat is sold, the monument can **continue on a new sat** while still **traversing historical inscriptions** on the old sat when needed.
- **Resolver** never treats a single layer as sole truth: **off-chain index + on-chain (entry sats + data sat)** form a **combined source of truth**.
- **Custody changes**: after a sale to a non-keeper party, **ignore** subsequent inscriptions on that entry sat for “current monument” purposes unless policy explicitly revives them (default: ignore).
- **Small text fixes** without full reinscription of large payloads may be expressed on the **data sat** as **targeted text replacements** against a specific **target inscription**.
- **Structural / non-text** changes (schema, nesting, new fields, binary media pointers, etc.) are **not** handled by text-patch records; use **reinscription on the appropriate entry sat** (or a new inscription the policy treats as authoritative for structure).

---

## 2. Terms

| Term | Meaning |
|------|--------|
| **monument_id** | Stable logical id for a monument (project), e.g. `bride_of_charlie`. |
| **entry sat** | The sat that currently (or historically) carries **this monument’s entry** inscriptions for a given logical record (episode, article, etc.). |
| **data sat** | Sat used for **registry** and **directive** inscriptions (see §4). May be **shared across monuments** or **overridden per monument** (§7). |
| **target inscription** | The on-chain inscription whose content is being referenced or patched; identified by **`inscription_id`** in directive payloads. |
| **keeper** | Party operating the monument; holds allowlisted wallets (§6). |

---

## 3. Combined source of truth

1. **Off-chain index** holds: fast lookups, **custody cutoffs**, **current_sat** (and history), optional mempool/preview flags, and **replay** of chain state the indexer has seen.
2. **On-chain** holds: immutable content, registry snapshots, and directives.
3. **Resolution rule:** the display pipeline **merges** outputs from both:
   - Apply **custody / sale cutoffs** from the index **before** treating any new reveal on an entry sat as part of the monument.
   - Apply **data sat** registry and directives **in chain order** (confirmed first for “canonical current”; see §8).
4. If **index** and **chain** disagree on something safety-critical (e.g. cutoff time), **prefer the more conservative** interpretation for public display until reconciled, and surface an **integrity warning** in UI/logs.

---

## 4. Data sat payloads

### 4.1 Registry (monument → current entry sat)

**Normative schema:** [`schemas/dia/registry.v1.json`](schemas/dia/registry.v1.json) (JSON Schema draft 2020-12). Validators MUST reject documents that fail schema validation or include unknown top-level properties (`additionalProperties: false`).

Example (illustrative):

```json
{
  "schema": "dia.registry.v1",
  "monuments": [
    { "monument_id": "bride_of_charlie", "current_sat": "1234567890123456789" }
  ],
  "updated_at": "block:890000"
}
```

- **Purpose:** on-chain **pointer** from `monument_id` to **current** entry sat for operational continuity after sales or migrations.
- **Initial state:** registry may be **empty**; off-chain index may bootstrap the first **seven** (or N) monuments until the first registry inscription lands.
- **Supersession:** newer confirmed registry inscription on the data sat **supersedes** older for pointer fields; **history** remains on-chain for audit.

### 4.2 Text directive (patch-like, text only)

**Normative schema:** [`schemas/dia/text_replace.v1.json`](schemas/dia/text_replace.v1.json). Validators MUST reject invalid documents the same way as for the registry.

For **small textual edits** to content already committed in a **target inscription**, inscribe on the **data sat** (or future policy may allow a dedicated “directives” inscription chain — v1: data sat).

Example (illustrative):

```json
{
  "schema": "dia.text_replace.v1",
  "monument_id": "bride_of_charlie",
  "inscription_id": "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefi0",
  "target": "teh",
  "replacement": "the",
  "occurrence_index": 0
}
```

- **`inscription_id`:** identifies the **target inscription** whose revealed content is the patch subject (not “any” inscription on a sat without id).
- **`occurrence_index`:** `0` = first match, `1` = second, …; **`-1`** = apply to **all** non-overlapping occurrences in order (specify exact algorithm in implementation: left-to-right, non-overlapping).
- **Applicability:** **plain text / UTF-8 string layers only** where substring replacement is unambiguous. If replacement would corrupt JSON structure, **reject** the directive for structured views and require **reinscription** (§5).

### 4.3 Out of scope for text directives

- Changing **keys**, **array shape**, **encoding**, **compressed blobs**, or **media**: use **reinscription** on the correct **entry sat** (or new entry sat after migration).

---

## 5. Reinscription vs data-sat directive

| Change type | Mechanism |
|-------------|-----------|
| Typos, single-string fixes in a text field | Data sat `dia.text_replace.v1` against **target inscription** (if safe) |
| JSON structure, new fields, renames, splits | New inscription on **entry sat** (appropriate sat per policy) |
| Large body rewrite | New inscription on **entry sat** |
| “Current pointer” after sale | Update **off-chain** immediately; then inscribe **registry** update on **data sat** when ready |

---

## 6. Custody, sale cutoffs, and keeper allowlist

### 6.1 Problem

If an **entry sat** is **sold** to a third party, that party can inscribe **after** the sale. Those inscriptions must **not** be treated as monument updates.

### 6.2 Off-chain behavior (authoritative for cutoff)

1. On detected **change of effective holder** for an entry sat:
   - If new holder **not** in **keeper allowlist** → set **`sale_cutoff_block_height`** (and/or timestamp, per indexer) for that sat for that **monument record**.
   - **Ignore** for monument resolution any inscription on that sat **after** the cutoff (per indexer’s ordering rules).
2. If the sat moves **only** between **allowlisted keeper wallets**, **do not** set a sale cutoff (internal ops).

### 6.3 Webhook / polling

- **Ideal:** webhook or job when **UTXO / holder** for tracked sats changes → immediate cutoff update.
- **Minimum:** periodic poll + manual keeper action to record cutoff if automation lags.
- **Display:** if cutoff is newer than the latest **indexed** inscription, show **“resolving custody — ignoring post-sale reveals”** when relevant.

### 6.4 Combined truth reminder

Cutoff lives **off-chain**; chain still contains post-sale inscriptions. The resolver **always** applies cutoff when building **monument-current** view. Historical browsers may still **list** post-sale inscriptions with label **“not part of monument (post-sale)”** for transparency.

---

## 7. Per-monument data sat override

- Default: one **shared data sat** for all monuments the keeper manages.
- Optional: `monument_id` config includes **`data_sat_id`** (or sat number) if a monument needs an isolated registry/directive stream.
- Resolver order: resolve **monument’s** data sat → apply registry + directives for that `monument_id` only.

---

## 8. Resolver algorithm (canonical “current” view)

**Inputs:** off-chain index (cutoffs, optional preview flags), all known **target inscriptions** for the logical record, **data sat** inscription stream (registry + directives).

1. **Confirmations:** use **confirmed** chain position for public “current.” Unconfirmed = preview only.
2. **Entry content:** select the **latest eligible** inscription on the **current entry sat** (from registry + index) that is **before any sale cutoff** for that sat (if set).
3. **Historical sats:** prior entry sats remain browsable; same cutoff rules apply per sat.
4. **Apply text directives:** walk **confirmed** `dia.text_replace.v1` records **in chain order** that reference the chosen **target inscription_id** (or descendants if policy chains replacements — v1: single target id per directive).
5. **Registry supersession:** latest confirmed registry wins for `current_sat` pointers.

**Tie-breaking** (if two candidates share height): deterministic secondary key (e.g. `txid`, then `vout`, then inscription id) — document exact choice in indexer code.

**Reorgs:** if the tip changes, recompute; cutoffs remain keyed to **block height / tx position** as stored, not “first seen.”

---

## 9. Operational checklist (keeper)

1. **Sale of entry sat:** update off-chain index **immediately** (cutoff + optional new `current_sat` on new sat). Inscribe **registry** update on data sat when feasible.
2. **Internal move:** ensure destination is **allowlisted**; no cutoff.
3. **Small text fix:** prefer **data sat** directive with explicit **target inscription_id**; verify JSON safety.
4. **Structural change:** **reinscribe** on entry sat; update index; optional registry if `current_sat` changes.

---

## 10. Open items (implementation)

- **Schema validation** in indexer/resolver CI: validate inscriptions against [`schemas/dia/registry.v1.json`](schemas/dia/registry.v1.json) and [`schemas/dia/text_replace.v1.json`](schemas/dia/text_replace.v1.json) when `schema` matches; reject unknown `schema` strings for v1 pipeline.
- **Substring replacement** semantics for Unicode normalization and combining characters.
- **Indexer** storage format for **cutoff history** and **replay**.
- **API** shape for monument web + monument display consumers.
- Whether multiple directives on the same target must carry **monotonic sequence numbers** to detect partial application.

---

## Related

- [`docs/AGENT_AND_MONUMENT_DECISIONS.md`](./AGENT_AND_MONUMENT_DECISIONS.md) — repo-wide monument notes.
