# Episode Analysis Protocol

This document defines the rules an analysis agent must follow when processing an episode in the Bride of Charlie investigation.

The goal is to produce a structured investigative record suitable for permanent inscription.

---

## Core Principles

### Artifact First
A claim cannot exist without an artifact.

Artifacts include:
- documents
- screenshots
- public records
- audio/video clips
- images
- quoted materials
- explicit confirmations

If the episode provides no artifact, the statement cannot be inscribed as a claim.

---

### No Rhetorical Drift
Do not inscribe:
- emotional commentary
- political rhetoric
- insults
- worldview statements
- narrative framing

unless the episode presents evidence supporting them.

---

### Preserve Exact Names
Do not normalize spelling unless certain.
If uncertain, preserve the name exactly as spoken and flag uncertainty.

---

### Chronology Preservation
Artifacts may include multiple timestamps.

Event Timestamp – when the event occurred

Source Timestamp – when the artifact first appeared

Video Timestamp – location in the episode

Discovery Timestamp – when investigators identified it

Extraction Timestamp – when it entered the archive

These timestamps allow reconstruction of:

• real‑world timeline
• public revelation timeline
• investigative discovery timeline
• archive ingestion timeline

---

## Structural Components

Artifacts

Claims

Nodes

These objects reference one another to form an investigative graph.

---

## Artifacts

Artifacts represent documentary evidence.

Examples:

court filings

obituaries

photos

yearbooks

public records

social media posts

interview clips

Artifacts use the A‑series numbering.

Bundles begin at **A‑1000**.

Sub‑artifacts use decimal numbering.

Example:

A‑1000 Court Filings

A‑1000.1 Separation Agreement (1995)

A‑1000.2 Separation Agreement (1996)

Artifacts must include a Related reference line linking claims and nodes.

---

## Nodes

Nodes represent persistent investigable entities.

Two categories exist.

People

Investigation targets

People numbering begins at **N‑1** in order of appearance.

Example:

N‑1 Charlie Kirk

N‑2 Erica Kirk

N‑3 Candace Owens

Investigation targets use the **1000 series**.

Example:

N‑1000 Date of Birth Discrepancy

N‑1001 Educational Timeline Gap

Nodes accumulate evidence across episodes.

---

## Claims

Claims are falsifiable statements supported by artifacts.

Each claim must pass three tests:

Artifact Anchor Test

Falsifiability Test

Rhetoric Removal Test

If any test fails, the statement must not be inscribed as a claim.

Claims use the **C‑1000** numbering series.

Example:

C‑1000 Repeated DOB Listed as November 22 1988

Each claim must reference:

Anchored Artifacts

Related Nodes

---

## Cross‑Reference Rule

Artifacts, nodes, and claims must reference one another.

Preferred format:

*Related: C‑1000, N‑2, N‑1000*

This produces a reversible investigative graph.

---

## Contradictions

Contradictions are recorded only when both sides are artifact‑anchored.

Example:

DOB in court filings vs public DOB used elsewhere.

Speculative contradictions must not be inscribed.

---

## Investigative Pressure

Nodes accumulate investigative pressure as evidence increases.

Each node records:

Evidence Count

Claim Count

Episode Count

This reveals where evidence converges.

---

## Required Output

Each analyzed episode must produce:

1. Meta‑Data

2. Executive Summary

3. Artifact Register

4. Node Register

5. Claim Register

6. Optional Flags

---

## Ledger Continuation Rule

The Bride of Charlie investigation uses a **global cross‑episode numbering ledger**.

Artifacts, claims, and nodes do **not restart numbering for each episode**.

Instead, every episode **continues the ledger from the highest existing identifier**.

Before analyzing a new episode, the agent must determine:

Highest Artifact ID

Highest Claim ID

Highest Node ID

The next episode must begin numbering from the next available value.

Example after Episode 1:

Artifacts: A-1000.1 → A-1000.21

Claims: C-1000 → C-1008

Nodes: N-1 → N-7

Episode 2 must therefore begin at:

Artifacts: A-1000.22

Claims: C-1009

Nodes: N-8 (only if a new node is required)

Existing nodes must **never be renumbered**.

If an artifact or claim references an existing node, the agent must reuse the same identifier.


## Episode Ledger Header

Each analyzed episode must include a ledger continuation summary in the metadata section.

Example:

Episode 2 Ledger Summary

Starting Artifact: A-1000.22
Ending Artifact: A-1000.32

Starting Claim: C-1009
Ending Claim: C-1013

New Nodes Introduced: N-8, N-9

This ensures the investigative ledger remains auditable and continuous across episodes.


## Correction Rule

Previously inscribed artifacts, claims, or nodes must **never be renumbered or rewritten**.

If a numbering error or misreference occurs, the correction must appear as a **new record** rather than altering existing entries.

Example:

Correction Note

A-1000.37 was referenced incorrectly in Episode 3.
Correct reference: A-1000.36.

The historical record must remain immutable.


## Final Rule

When uncertain, preserve less and preserve carefully.

The goal is structural integrity, not maximum volume.

