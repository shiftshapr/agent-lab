# Meta-Layer World Model – Neo4j Schema (Revised)

This version fixes the original model so it reflects the actual meta-layer worldview found across the source materials.

It is **not** a book-only schema. It is a **world model for the meta-layer stack**: primitives, overlays, governance, trust, presence, communities, containment, and supporting source material.

## Design principles

1. Model the **meta-layer as civic interface infrastructure above the webpage**.
2. Separate **world concepts** from **source evidence**.
3. Represent both **technical primitives** and **governance primitives**.
4. Keep extraction-friendly nodes for notes, PDFs, and future ingestion.
5. Avoid vague labels that do not map to the real architecture.

---

## What was wrong with the original

The original schema mixed three different things into one layer:

- real meta-layer architecture
- note-taking / ideation residue
- generic knowledge management types

That made it feel more like a personal notebook ontology than a reality-based world model.

### Main problems

- `MLIdea`, `MLDream`, and `MLOpportunity` are not core world-model entities.
- `MLPrimitive` mixed actual meta-layer primitives with broad words like `trust`, `layer`, and `signal`.
- `MLEntity` was too vague for humans, agents, coalitions, and institutions.
- `MLReport` and `MLSource` overlapped.
- There was no first-class place for:
  - overlay applications
n  - smart tags
  - smart filters
  - presence
  - decentralized identity
  - trust signals
  - policies / governance rules
  - consent structures
  - AI agents / containment
  - meta-communities

So the schema below restructures around the actual stack.

---

# Core model

## 1) Knowledge and evidence layer

These nodes let you ingest books, papers, PDFs, web pages, notes, and extracted passages.

### `MLSource`
A provenance object for any ingested source.

**Properties**
- `id`
- `title`
- `source_type` (`book`, `paper`, `pdf`, `website`, `note`, `canvas`, `transcript`, `spec`, `draft`)
- `author`
- `publisher`
- `url`
- `path`
- `source_date`
- `ingested_at`
- `summary`

### `MLChunk`
A paragraph, excerpt, section summary, quote, or extracted unit from a source.

**Properties**
- `id`
- `text`
- `chunk_type` (`paragraph`, `excerpt`, `summary`, `quote`, `section`)
- `section_title`
- `page_start`
- `page_end`
- `source_date`
- `created_at`

### `MLClaim`
A normalized proposition extracted from one or more chunks.

**Properties**
- `id`
- `statement`
- `claim_type` (`definition`, `assertion`, `prediction`, `design_principle`, `requirement`)
- `confidence`
- `status` (`draft`, `reviewed`, `contested`, `accepted`)

---

## 2) Conceptual layer

These represent the worldview itself.

### `MLConcept`
A general concept in the meta-layer worldview.

**Examples**
- collective intelligence
- cognitive freedom
- contextual integrity
- interface-level governance
- trust orchestration
- civic overlay
- sociotechnical containment

**Properties**
- `name`
- `definition`
- `domain` (`governance`, `trust`, `interface`, `identity`, `ai`, `coordination`, `civic`, `knowledge`)

### `MLPrimitive`
A first-class meta-layer primitive or substrate capability.

**Use this only for actual primitives, not any important noun.**

**Examples**
- Overlay Application
- Smart Tag
- Smart Filter
- Presence
- Meta-Community
- Unique ID / DID
- Trust Signal
- Consent Scaffold
- Policy Zone
- Bridge

**Properties**
- `name`
- `definition`
- `primitive_class` (`technical`, `governance`, `interface`, `identity`, `coordination`)
- `examples`

### `MLFramework`
A named model, architecture, or mental model.

**Examples**
- Metaweb
- Meta-Layer
- Overweb Pattern
- Sociotechnical Trust Stack
- Safe-AI Trifecta
- Web Cake
- Quantum Octaves

**Properties**
- `name`
- `description`
- `use_case`
- `status` (`conceptual`, `draft`, `active`, `research`)

### `MLUseCase`
A recurring application pattern enabled by the meta-layer.

**Examples**
- safe digital space
- on-page presence
- contextual trust overlays
- AI containment above the webpage
- cross-site civic annotation
- provenance display

**Properties**
- `name`
- `description`
- `maturity` (`vision`, `prototype`, `active`)

---

## 3) Infrastructure and interaction layer

These model the actual operational stack.

### `MLOverlayApp`
An application running above web content across relevant pages.

**Examples**
- Canopi
- a sidebar chat overlay
- a contextual warning layer

**Properties**
- `name`
- `description`
- `app_type`
- `status`
- `url`

### `MLTag`
A smart tag or contextual marker attached to a snippet, object, region, or page.

**Examples**
- citation tag
- warning tag
- bridge tag
- poll tag
- conversation tag

**Properties**
- `name`
- `tag_type`
- `description`
- `trigger_type` (`attention`, `manual`, `rule`, `agentic`)

### `MLTrustSignal`
A visible trust-relevant signal surfaced at the interface.

**Examples**
- provenance marker
- AI-generated content label
- identity verification signal
- community endorsement
- runtime attestation

**Properties**
- `name`
- `signal_type`
- `description`
- `verification_method`
- `display_mode`

### `MLPolicy`
A policy, rule set, or governance instruction applied in a community or context.

**Examples**
- bot exclusion policy
- medical claim review rule
- consent requirement for AI intervention

**Properties**
- `name`
- `policy_type` (`moderation`, `consent`, `identity`, `ai`, `visibility`, `trust`)
- `description`
- `enforcement_mode` (`social`, `interface`, `cryptographic`, `hybrid`)
- `status`

### `MLConsentRule`
A specific consent boundary, permission, or interaction contract.

**Properties**
- `name`
- `description`
- `scope` (`session`, `community`, `app`, `agent`, `data`)
- `revocable` (`true`/`false`)

### `MLIdentity`
A decentralized or application-level identity object.

**Properties**
- `id`
- `identity_type` (`DID`, `wallet`, `pseudonymous`, `verified_human`, `organization`)
- `issuer`
- `verification_status`

### `MLPresenceMode`
A mode of participant presence in the meta-layer.

**Examples**
- ambient
- anonymous
- visible
- actively signaling

**Properties**
- `name`
- `description`

### `MLFilter`
A smart filter that includes, excludes, ranks, or modifies visible overlay content.

**Properties**
- `name`
- `filter_type` (`trust`, `community`, `topic`, `identity`, `risk`, `visibility`)
- `description`
- `scope`

---

## 4) Social and governance layer

### `MLCommunity`
A meta-community, working group, civic group, or persistent overlay collective.

**Properties**
- `name`
- `description`
- `community_type` (`civic`, `research`, `governance`, `project`, `learning`)
- `url`
- `status`

### `MLActor`
A person, agent, organization, or collective actor.

This replaces the vague `MLEntity`.

**Properties**
- `name`
- `actor_type` (`person`, `ai_agent`, `organization`, `coalition`, `institution`, `community`)
- `description`
- `url`

### `MLRole`
A role an actor can hold in a community or governance process.

**Examples**
- participant
- steward
- moderator
- developer
- researcher
- policy keeper

**Properties**
- `name`
- `description`

### `MLGovernanceModel`
A reusable governance structure or pattern.

**Examples**
- composable governance
- rough consensus
- delegated moderation
- community policy stack

**Properties**
- `name`
- `description`
- `governance_type`

---

## 5) AI and containment layer

### `MLAgent`
A specific AI agent or agent class operating in the meta-layer.

**Properties**
- `name`
- `agent_type`
- `description`
- `visibility_requirement`
- `status`

### `MLContainmentPattern`
A containment, safety, or oversight pattern.

**Examples**
- interface-level containment
- runtime governance
- consent stack
- secure enclave execution
- community auditability

**Properties**
- `name`
- `description`
- `containment_type` (`technical`, `social`, `hybrid`)

### `MLRuntimeBoundary`
A technical enforcement boundary.

**Examples**
- Trusted Execution Environment
- secure enclave
- policy enforcement zone

**Properties**
- `name`
- `boundary_type`
- `description`

---

## 6) Optional research layer

Only keep this if you want the graph to also cover speculative R&D.

### `MLResearchTrack`
A future-facing area of investigation.

**Examples**
- Quantum Octaves
- hyperdimensional computation
- octonion-based AI architectures

**Properties**
- `name`
- `description`
- `status` (`speculative`, `research`, `prototype`)

---

# Recommended relationships

## Provenance and evidence
- `(:MLSource)-[:CONTAINS]->(:MLChunk)`
- `(:MLChunk)-[:SUPPORTS]->(:MLClaim)`
- `(:MLChunk)-[:CONTRADICTS]->(:MLClaim)`
- `(:MLClaim)-[:ABOUT]->(:MLConcept)`
- `(:MLClaim)-[:ABOUT]->(:MLPrimitive)`
- `(:MLClaim)-[:ABOUT]->(:MLFramework)`

## Conceptual structure
- `(:MLFramework)-[:USES_CONCEPT]->(:MLConcept)`
- `(:MLFramework)-[:USES_PRIMITIVE]->(:MLPrimitive)`
- `(:MLConcept)-[:RELATES_TO]->(:MLConcept)`
- `(:MLConcept)-[:DERIVES_FROM]->(:MLConcept)`
- `(:MLUseCase)-[:REQUIRES]->(:MLPrimitive)`
- `(:MLUseCase)-[:IMPLEMENTS_CONCEPT]->(:MLConcept)`
- `(:MLFramework)-[:ENABLES]->(:MLUseCase)`

## Infrastructure
- `(:MLOverlayApp)-[:IMPLEMENTS]->(:MLPrimitive)`
- `(:MLOverlayApp)-[:USES_TAG]->(:MLTag)`
- `(:MLOverlayApp)-[:DISPLAYS]->(:MLTrustSignal)`
- `(:MLOverlayApp)-[:APPLIES_FILTER]->(:MLFilter)`
- `(:MLTag)-[:ATTACHED_TO]->(:MLChunk)`
- `(:MLTag)-[:INSTANTIATES]->(:MLConcept)`
- `(:MLTrustSignal)-[:VERIFIES]->(:MLIdentity)`
- `(:MLTrustSignal)-[:SUPPORTS]->(:MLClaim)`
- `(:MLFilter)-[:FILTERS]->(:MLTag)`
- `(:MLFilter)-[:FILTERS]->(:MLTrustSignal)`

## Governance and communities
- `(:MLActor)-[:MEMBER_OF]->(:MLCommunity)`
- `(:MLActor)-[:HOLDS_ROLE]->(:MLRole)`
- `(:MLRole)-[:IN]->(:MLCommunity)`
- `(:MLCommunity)-[:USES_GOVERNANCE]->(:MLGovernanceModel)`
- `(:MLCommunity)-[:ADOPTS_POLICY]->(:MLPolicy)`
- `(:MLPolicy)-[:IMPLEMENTS_CONSENT]->(:MLConsentRule)`
- `(:MLPolicy)-[:GOVERNS]->(:MLOverlayApp)`
- `(:MLPolicy)-[:GOVERNS]->(:MLAgent)`

## Presence and identity
- `(:MLActor)-[:HAS_IDENTITY]->(:MLIdentity)`
- `(:MLActor)-[:USES_PRESENCE_MODE]->(:MLPresenceMode)`
- `(:MLCommunity)-[:ALLOWS_PRESENCE_MODE]->(:MLPresenceMode)`

## AI containment
- `(:MLAgent)-[:BOUND_BY]->(:MLPolicy)`
- `(:MLAgent)-[:CONSTRAINED_BY]->(:MLContainmentPattern)`
- `(:MLContainmentPattern)-[:ENFORCED_BY]->(:MLRuntimeBoundary)`
- `(:MLRuntimeBoundary)-[:SECURES]->(:MLOverlayApp)`

## Research
- `(:MLResearchTrack)-[:INFORMS]->(:MLFramework)`
- `(:MLResearchTrack)-[:RELATES_TO]->(:MLConcept)`

---

# Analysis layer (applied to everything)

A second layer that runs on **all** ingested content—notes, PDFs, URLs, Logseq—regardless of whether it maps to the meta-layer world model.

## Analysis nodes (no ML prefix—not meta-layer)

Everything gets analyzed for:

- **Dream** — Literal overnight dreams (from [[Dream]] tag) or aspirations
- **Opportunity** — Alignment, collaboration, promotion signals
- **Insight** — Non-obvious realizations, learnings, "aha" moments
- **Idea** — Projects, experiments, articles, workshops, thought experiments, inscriptions
- **Theme** — Recurring topics across notes
- **Milestone** — Progress markers, goals reached, key events

These are **not** world-model entities. They are research/ideation residue—useful for retrieval, synthesis, and opportunity tracking, but separate from the reality layer.

**Relationship:** `(:MLSource)-[:CONTAINS]->(:MLChunk)` and analysis nodes `[:EMERGES_FROM]->(:MLSource)`.

---

# "Add to meta-layer" vs "Add to graph"

- **Add to graph** — Ingest + analysis layer (Dream, Opportunity, Insight, Idea, Theme, Milestone). All content gets this.
- **Add to meta-layer** — Ingest + analysis layer + **meta-layer mapping**. The mapping step extracts MLConcept, MLPrimitive, MLFramework, MLActor, etc. **only when content aligns or extends the meta-layer world model.**

Example: Logseq has many ideas. Some are meta-layer concepts (Overweb, Smart Tags, collective intelligence) and merit deeper treatment—mapping to the world model. Others are personal ideas that stay in the analysis layer only.

---

# Minimal viable schema

If you want the smallest reality-based version, start with these labels only:

- `MLSource`
- `MLChunk`
- `MLClaim`
- `MLConcept`
- `MLPrimitive`
- `MLFramework`
- `MLUseCase`
- `MLOverlayApp`
- `MLTag`
- `MLTrustSignal`
- `MLPolicy`
- `MLCommunity`
- `MLActor`
- `MLIdentity`
- `MLAgent`
- `MLContainmentPattern`

That is enough to represent the actual meta-layer worldview.

---

# Suggested uniqueness constraints

```cypher
CREATE CONSTRAINT ml_source_id IF NOT EXISTS
FOR (n:MLSource) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT ml_chunk_id IF NOT EXISTS
FOR (n:MLChunk) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT ml_claim_id IF NOT EXISTS
FOR (n:MLClaim) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT ml_concept_name IF NOT EXISTS
FOR (n:MLConcept) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_primitive_name IF NOT EXISTS
FOR (n:MLPrimitive) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_framework_name IF NOT EXISTS
FOR (n:MLFramework) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_usecase_name IF NOT EXISTS
FOR (n:MLUseCase) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_overlayapp_name IF NOT EXISTS
FOR (n:MLOverlayApp) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_tag_name IF NOT EXISTS
FOR (n:MLTag) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_trustsignal_name IF NOT EXISTS
FOR (n:MLTrustSignal) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_policy_name IF NOT EXISTS
FOR (n:MLPolicy) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_community_name IF NOT EXISTS
FOR (n:MLCommunity) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT ml_identity_id IF NOT EXISTS
FOR (n:MLIdentity) REQUIRE n.id IS UNIQUE;
```

---

# Suggested full-text indexes

```cypher
CREATE FULLTEXT INDEX ml_chunk_text IF NOT EXISTS
FOR (n:MLChunk) ON EACH [n.text];

CREATE FULLTEXT INDEX ml_claim_statement IF NOT EXISTS
FOR (n:MLClaim) ON EACH [n.statement];

CREATE FULLTEXT INDEX ml_source_title IF NOT EXISTS
FOR (n:MLSource) ON EACH [n.title, n.summary];
```

---

# Example world-model spine

A clean example of how this graph should read:

```text
Meta-Layer (MLFramework)
  USES_PRIMITIVE -> Smart Tag (MLPrimitive)
  USES_PRIMITIVE -> Presence (MLPrimitive)
  USES_PRIMITIVE -> Smart Filter (MLPrimitive)
  USES_PRIMITIVE -> Unique ID / DID (MLPrimitive)
  ENABLES -> Safe Digital Space (MLUseCase)
  ENABLES -> On-Page Presence (MLUseCase)
  ENABLES -> AI Containment Above the Webpage (MLUseCase)

Canopi (MLOverlayApp)
  IMPLEMENTS -> Overlay Application (MLPrimitive)
  DISPLAYS -> Presence Verification (MLTrustSignal)
  APPLIES_FILTER -> Community Safety Filter (MLFilter)

Medical Integrity Community (MLCommunity)
  ADOPTS_POLICY -> Verified Medical Claim Policy (MLPolicy)
  USES_GOVERNANCE -> Composable Governance (MLGovernanceModel)

Clinical Review Agent (MLAgent)
  BOUND_BY -> Verified Medical Claim Policy (MLPolicy)
  CONSTRAINED_BY -> Interface-Level Containment (MLContainmentPattern)

TEE Boundary (MLRuntimeBoundary)
  SECURES -> Canopi (MLOverlayApp)
```

---

# Separation from Bride of Charlie

Keep the namespace separation.

Bride of Charlie can continue using:
- `Artifact`
- `Claim`
- `Node`
- `Person`
- `Episode`

Meta-layer should remain isolated with `ML*` labels.

That is a good call.

---

# Final recommendation

Use a **three-zone ontology**:

## Zone A – reality layer
For the actual meta-layer world model:
- concepts
- primitives
- frameworks
- use cases
- apps
- tags
- trust signals
- policies
- communities
- identities
- agents
- containment

## Zone B – evidence layer
For source grounding:
- sources
- chunks
- claims

## Zone C – optional research layer
For exploratory work:
- hypotheses
- proposals
- speculative research tracks

That will make the graph usable for:
- knowledge extraction
- architecture mapping
- governance design
- source-grounded synthesis
- future agentic tooling

It will also make it much closer to reality.

