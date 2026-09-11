# Episode Analysis Output Template

Use this structure for each analyzed episode. Follow the protocol rules in `ep_protocol_v2.md`.

**CRITICAL: ID numbering is GLOBAL across episodes. NEVER reuse artifact (A-) or claim (C-) IDs from previous episodes. The ledger context tells you the next available IDs — use ONLY those.**

---

## 1. Meta-Data

- **Episode**: [number or identifier]
- **Source**: [video/audio source]
- **Video Timestamp Range**: [start–end if applicable]
- **Extraction Timestamp**: [when analyzed]
- **Episode Ledger Summary**:
  - Artifact Families Introduced: A-XXXX, A-XXXX, ...
  - Claim Range: C-XXXX–C-XXXX
  - New Nodes Introduced: N-X, N-Y (if any)
  - Existing Nodes Reused: N-1, N-2, ... (if any)

---

## 2. Executive Summary

[2–4 sentences. Artifact-anchored only. No rhetoric.]

---

## 3. Artifact Register

**A-XXXX** [Bundle Name – one evidentiary family per top-level ID]

**A-XXXX.1** [Individual artifact description]

Event Timestamp: [date]
Source Timestamp: [date]
Video Timestamp: [HH:MM:SS]
Discovery Timestamp: [date]

*Related: C-XXXX, N-X, N-1000*

(Repeat for each artifact family. Create new family when evidentiary source changes.)

---

## 4. Node Register

**N-X** [Person Name]

[Short descriptive line explaining why this node matters.]

Evidence Count: [count]
Claim Count: [count]
Episode Count: [count]
Investigative Pressure: [Low/Medium/High]

*Related: A-XXXX.1, C-XXXX, C-YYYY*

---

**N-1000** [Investigation Target Name]

[Short descriptive line explaining the discrepancy or verification question.]

Evidence Count: [count]
Claim Count: [count]
Episode Count: [count]
Investigative Pressure: [Low/Medium/High]

*Related: A-XXXX.2, C-ZZZZ, N-X*

(Repeat for each node. People use N-1 through N-999. Investigation targets use N-1000+.)

---

## 5. Claim Register

**C-XXXX** [Short claim label]

Claim Timestamp: HH:MM:SS
Claim: [One-sentence neutral description.]
Anchored Artifacts: A-XXXX.1, A-XXXX.2
Related Nodes: N-X, N-1000
Investigative Direction: [What could verify or falsify the claim.]

---

## 6. Optional Flags

- [Uncertainty flags]
- [Correction notes if applicable]
- [Contradictions (both sides artifact-anchored)]

---

## Extract guidance (read/display sources)

Apply these rules during extraction and Phase 2 drafting:

1. **Read or displayed = Artifact.** Any source the host **reads aloud** or **displays on-screen** — tweet/X post, article, news clip, IG reel, email, Substack excerpt, fan comment — is an **Artifact** (with `transcript_snippet` grounded to `transcripts_corrected`).
2. **Host agreement/disagreement = Claim.** When the host **concurs with**, **rejects**, or **qualifies** a thesis presented in that read/displayed source, capture that as a **Claim** anchored to the artifact — not as rhetoric-only.
3. **Related Nodes include author.** When a read/displayed source has a named author, poster, or account, include that **Person** (or account-as-node when appropriate) in the artifact's and claim's **Related Nodes**.
4. **Anti-pattern:** Do **not** treat read-aloud/displayed third-party text as host rhetoric only. If it appears in the transcript as quoted or shown material, it needs artifact (and usually claim) rows.
5. **Cautionary example — Lane-class miss:** Episode 1 **Elizabeth Lane** viral X post (`A-1009.1`) was initially under-extracted when treated as framing-only. Correct pattern: artifact for the post read in full + claim for Lane's thesis + separate claim for host concurrence (`C-1008`, `C-1009`), with **N-6 Elizabeth Lane** in Related Nodes.
