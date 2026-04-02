# OpenClaw – Episode Analysis Protocol

This protocol tells an analysis agent how to process a single episode in the Bride of Charlie investigation and produce an inscription-ready record.

The agent's job is to preserve investigative structure, not to preserve rhetoric.

---

## Core Principles

### Artifact First
A claim may be inscribed only if the episode presents at least one artifact supporting it.

### No Rhetorical Drift
Do not inscribe scene-setting rhetoric, political venting, insults, worldview statements, or speculative expansion as claims.

### Preserve Exact Names (transcripts vs node names)
In **transcript snippets** and **quotes**, preserve wording as spoken/captioned unless an **editorial pass** applies. For **node `name` fields** and **investigative labels**, use the project’s **canonical spelling** for known proper names (schools, programs, agencies) and record STT variants in **`also_known_as`** or notes. If uncertain, preserve the transcript form and flag uncertainty.

### Preserve Chronology
Capture timestamps when available.

Required artifact timestamps:
- Event Timestamp
- Source Timestamp
- Video Timestamp
- Discovery Timestamp

Optional:
- Extraction Timestamp

### Claims Are Propositions, Nodes Are Containers
Claims are falsifiable statements tied to artifacts.
Nodes are persistent investigable people, entities, discrepancies, or verification targets.

### Cross-Reference Everything
Artifacts, claims, and nodes must all reference one another.

---

## Required Output Structure

Each analyzed episode must produce these sections in this order:

1. Meta-Data
2. Executive Summary
3. Artifact Register
4. Node Register
5. Claim Register
6. Optional Flags

---

# I. Meta-Data

Capture:
- Episode title
- Series title
- Episode number if known
- Channel / creator
- Episode date if known
- Source used for analysis (video, transcript, or both)
- Transcript completeness status
- Analyst / agent name
- Analysis date
- Ledger continuation summary

If unknown, write Unknown. Do not guess.

---

# II. Executive Summary

Write a short archival summary.

Length:
- 1 to 3 short paragraphs

Focus on:
- what evidentiary material is presented
- what investigative questions are advanced
- what structural importance the episode has in the series

Do not speculate.
Do not write persuasively.

---

# III. Artifact Register

## What counts as an artifact
An artifact is something shown, cited, quoted from, or explicitly presented as documentary support.

Examples:
- court filing
- screenshot
- yearbook image
- obituary
- social media post
- audio clip
- interview clip
- public record
- testimonial confirmation explicitly claimed in the episode

## What does not count as an artifact
- host opinion
- inference
- emotional framing
- unsupported allegation
- broad theory

## Artifact numbering model
Artifacts are numbered by **family**, not by episode.

Top-level artifact IDs are global across the series:
- A-1000
- A-1001
- A-1002
- A-1003

Sub-artifacts are local to one family only:
- A-1000.1
- A-1000.2
- A-1001.1

## Family rule
A family is a set of artifacts from the same evidentiary source or record family.

Valid families include:
- multiple pages from the same court filing set
- documents from the same proceeding
- frames or segments from the same interview clip
- images from the same Instagram story sequence
- pages from the same obituary or yearbook entry

Create a **new top-level artifact ID whenever the evidentiary family changes**.

### Invalid structure
Do not do this:

A-1000 Episode Bundle
A-1000.1 divorce filing
A-1000.2 Instagram story
A-1000.3 obituary
A-1000.4 podcast clip

That mixes unrelated evidence types into one family.

### Correct structure
Do this instead:

A-1000 Court Filing Bundle
A-1000.1 Separation Agreement (1995)
A-1000.2 Separation Agreement (1996)

A-1001 Instagram Story Bundle
A-1001.1 Erika at Universal Studios
A-1001.2 Uncle Rick appears

A-1002 Obituary Bundle
A-1002.1 Obituary: Angelina Lombardo-Abbis (1970)

## Single-artifact rule
If an artifact stands alone, it still gets its own top-level family with one sub-item.

Example:

A-1003 Yearbook Bundle
A-1003.1 St Ursula Villa Kindergarten Photo

## Artifact format
Use this exact structure:

**A-1000** Bundle Name

**A-1000.1** Individual artifact description

Event Timestamp: YYYY-MM-DD or descriptive date
Source Timestamp: YYYY-MM-DD or descriptive date
Video Timestamp: HH:MM:SS
Discovery Timestamp: YYYY-MM-DD or descriptive date
Extraction Timestamp: YYYY-MM-DD HH:MM UTC (optional)
Confidence Level: High / Medium / Low (optional)

*Related: C-1000, N-2, N-1000*

If a timestamp is unknown, omit it rather than guessing.

## Artifact description rules
- Be literal
- Be concise
- Identify what the artifact is, not what it proves

## Bundle sanity check
Before finalizing, verify:
- no episode-wide artifact bundle exists
- each top-level artifact ID represents one evidentiary family only
- unrelated artifact types use different top-level IDs
- single artifacts still receive their own family

---

# IV. Node Register

## What is a node
A node is a persistent investigable entity or target that remains meaningful even if one claim is removed.

## Node categories
### People
People start at N-1 and are numbered in order of appearance in the series ledger.

Example:
- N-1 Charlie Kirk
- N-2 Erika Kirk
- N-3 Candace Owens

### Investigation targets
Non-person targets use the 1000 series.

Examples:
- N-1000 Date of Birth Discrepancy
- N-1001 Educational Timeline Gap
- N-1002 Lombardi Genealogical Verification Question
- N-10xx **MK Ultra** (historical program — when discussed as a target of investigation)
- N-10xx **CIA Project Looking Glass** (when discussed as a distinct program — separate from a school that shares wording in the transcript)

## What should become a node
Create a node when the thing is:
- a person appearing in artifact-backed claims
- a discrepancy
- a timeline gap
- a relationship requiring verification
- an institution or entity repeatedly involved
- a persistent unresolved target
- **a named government program, agency initiative, or institutional program** (e.g. **MK Ultra**, a **CIA** program such as **Project Looking Glass**, a legislative or military program) when the episode discusses it **substantively** — **even a single mention in the series**. Recurrence across episodes is **not** required. Use **`InvestigationTarget`** (or **`institution`** when the schema calls for it) with a clear **`name`** and link claims/artifacts to that node.

## Programs vs memes
- **Nodes** hold **named, investigable entities** (people, institutions, **programs**, discrepancies).
- **Memes** (M-*) capture **cross-cutting rhetorical / euphemism / code patterns** (how language is used). **Do not** use a meme row as a substitute for a **program or institution node** when the episode names a real program or body. You may have **both**: e.g. a node for **CIA Project Looking Glass** and a meme analyzing how the host links “Looking Glass School” to that name.

## What should not become a node
Do not create nodes for:
- rhetorical phrases
- general themes
- host emotions
- broad political ideas
- unsupported macro-theories

## Node format
Use this exact structure:

**N-2** Erika Kirk

Short descriptive line explaining why this node matters.

Evidence Count: 0
Claim Count: 0
Episode Count: 0
Investigative Pressure: Low / Medium / High (optional during single-episode analysis)

*Related: A-1000.1, A-1004.2, C-1000, C-1003*

## Node naming rule
Node names must be stable and investigable. Use **canonical English spellings** for established proper names (schools, programs, places) when known — e.g. **Tesseract** for the school brand if that is the project’s house spelling — and use **`also_known_as`** in structured extraction for transcript variants (**Tesaract**, caption misspellings).

Good:
- Lombardi Genealogical Verification Question
- Tesseract School Investigation (with also_known_as: Tesaract, etc., if STT varies)

Bad:
- Lombardi Lie
- **Tesaract School Investigation** as the **sole** display name when the canonical institution name is **Tesseract** (fix the `name`; keep STT forms as aliases)

---

# V. Claim Register

## What is a claim
A claim is a falsifiable assertion presented in the episode as supported by evidence.

## Claim admission test
A statement may enter the Claim Register only if it passes all three tests:

1. Artifact Anchor Test – at least one artifact in the episode supports it
2. Falsifiability Test – it could in principle be verified, disproved, clarified, or resolved
3. Rhetoric Removal Test – it still matters investigatively when emotional framing is removed

If any test fails, do not inscribe it as a claim.

Recommended failure labels:
- Framing Premise
- Speculation
- Interpretive Commentary
- Narrative Expansion
- Unsupported Allegation

## Claim numbering
Claims use the global C-1000 series.

## Claim format
Use this exact structure:

**C-1000** Short claim label

Claim Timestamp: HH:MM:SS

Claim: One-sentence neutral description.

Anchored Artifacts: A-1000.1, A-1000.2

Related Nodes: N-2, N-1000

Investigative Direction: One sentence describing what could verify or falsify the claim.

If Claim Timestamp is unknown, omit it rather than guessing.

## Claim description rules
- Neutral wording
- No rhetorical charge
- No adjectives implying guilt unless the artifact itself is a formal finding
- Preserve scope faithfully

---

# VI. Cross-Reference Rule

Artifacts, nodes, and claims must all reference one another.

Preferred format:

*Related: C-1000, N-2, N-1000*

Claims must include:
- Anchored Artifacts
- Related Nodes

Artifacts must include:
- Related claims
- Related nodes

Nodes must include:
- Related artifacts
- Related claims

This creates a reversible investigative graph.

---

# VII. Framing vs Claims

Do not confuse framing premises with evidence-backed claims.

Examples of framing premises:
- This was an assassination
- They are lying
- This was a military operation

These do not belong in the Claim Register unless the episode presents artifact-backed support for them in that episode.

---

# VIII. Contradictions

Only record contradictions when both sides are artifact-anchored.

A contradiction is inscription-worthy if:
- claim A is backed by an artifact
- claim B is backed by an artifact
- both cannot comfortably coexist without clarification

Do not inflate every inconsistency into a contradiction.

---

# IX. Global Ledger Continuation Rule

The Bride of Charlie investigation uses a **global cross-episode numbering ledger**.

Artifacts, claims, and nodes do not restart for each episode.

## Critical: Never reuse IDs
**Artifact and claim IDs from previous episodes are FORBIDDEN.** The ledger context tells you the next available IDs. Use only those. Reusing an ID (e.g. using A-1007 when A-1007 already exists in Episode 1) corrupts the investigative record.

## Before analyzing a new episode, determine:
- highest existing top-level artifact family ID
- highest existing claim ID
- highest existing node ID

## Continuation example
If the ledger currently contains:
- A-1000
- A-1001
- A-1002
- A-1003
- C-1000 to C-1008
- N-1 to N-7

then the next episode begins with:
- next artifact family: A-1004
- next claim: C-1009
- next node: N-8 only if a new node is required

Sub-artifacts are always internal to the family.

Example:

A-1004 Court Filing Bundle
A-1004.1 Separation Agreement (1995)
A-1004.2 Separation Agreement (1996)

Existing nodes must never be renumbered.
If a claim or artifact references an existing node, reuse that node ID.

## Episode ledger header
Each analyzed episode must include:

Episode X Ledger Summary

Artifact Families Introduced:
A-1004
A-1005
A-1006

Claim Range: C-1009–C-1013

New Nodes Introduced: N-8, N-9

Existing Nodes Reused: N-1, N-2, N-5

## Correction rule
Previously inscribed artifacts, claims, or nodes must never be renumbered or rewritten.

If a numbering error occurs, correct it with a new correction record.

Example:

Correction Note
A-1006 was referenced incorrectly.
Correct reference: A-1005.

---

# X. Investigative Pressure

Nodes accumulate investigative pressure as evidence increases.

Each node records:
- Evidence Count
- Claim Count
- Episode Count

This reveals where evidence converges.

---

# XI. Optional Flags

Use only when needed.

Allowed flags:
- Name uncertainty
- Artifact verbally referenced but not shown
- Transcript ambiguity
- Timestamp uncertainty
- Possible transcription error
- Requires human verification
- Claim failed admission test

Do not use Optional Flags for theory commentary.

---

# XII. Output Quality Checklist

Before finalizing, verify:
- every claim has at least one artifact anchor
- every claim has at least one node
- every artifact has a Related line
- every node has a Related line
- no episode-wide artifact bundle exists
- people nodes use the global people ledger
- non-person investigation targets use the 1000 series
- no speculative claims were inscribed as evidence-backed claims
- names are preserved exactly or uncertainty is noted
- formatting is consistent

---

# XIII. Minimal Example

## Meta-Data
- Episode: Bride of Charlie 4
- Channel: Candace Owens
- Source Format: Transcript + video
- Analysis Date: 2026-03-11
- Episode Ledger Summary:
  - Artifact Families Introduced: A-1004, A-1005, A-1006
  - Claim Range: C-1009–C-1013
  - New Nodes Introduced: N-8, N-9
  - Existing Nodes Reused: N-1, N-2, N-5

## Artifact Register
**A-1004** Court Filing Bundle

**A-1004.1** Court Filing: Separation Agreement (1995)

Event Timestamp: 1995
Source Timestamp: 1995 filing date
Video Timestamp: 00:42:18
Discovery Timestamp: 2026-03-11
Extraction Timestamp: 2026-03-11 19:22 UTC
Confidence Level: High

*Related: C-1009, N-2, N-1000*

## Node Register
**N-2** Erika Kirk

Primary biographical subject of the episode's evidentiary claims.

Evidence Count: 2
Claim Count: 2
Episode Count: 1
Investigative Pressure: Medium

*Related: C-1009, C-1010, A-1004.1, A-1005.1, N-1000*

**N-1000** Date of Birth Discrepancy

Persistent inconsistency between documented DOB and publicly used DOB.

Evidence Count: 2
Claim Count: 1
Episode Count: 1
Investigative Pressure: Medium

*Related: C-1009, A-1004.1, A-1004.2, N-2*

## Claim Register
**C-1009** Repeated DOB Listed as November 22, 1988

Claim Timestamp: 00:42:18

Claim: The episode presents that Erika's DOB appears as November 22, 1988 across multiple filings.

Anchored Artifacts: A-1004.1, A-1004.2

Related Nodes: N-2, N-1000

Investigative Direction: Obtain certified copies of the filings and compare them against official identity records.

---

## Final Rule

When uncertain, preserve less and preserve more carefully.

The goal is structural integrity, not maximum volume.
