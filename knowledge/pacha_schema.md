# Pacha World Model — Neo4j Schema

This schema treats **Pacha’s Pajamas** as a **separate story ontology** from the tech/framework meta-layer.  
It lives alongside the meta-layer graph in the same Neo4j database, sharing ingestion patterns (Source → Chunk → Claims) but using a distinct narrative-focused node vocabulary.

---

## 1. Purpose

Model the **story world** of Pacha in Neo4j so narrative elements can be extracted, linked, queried, and expanded across books, treatments, decks, and future scripts.

It should capture:

- Characters
- Family and dream mirrors
- Realms and locations
- Biomes and ecology
- Magical objects and portals
- Stories, scenes, arcs, and quests
- Conflicts and transformations
- Themes, symbols, songs, and ritual/performance
- Source evidence and canon status

---

## 2. Separation from the Meta-Layer

**Meta-layer ontology** = tech/framework/civic/DAO concepts  
**Pacha ontology** = narrative/story/world concepts

They can coexist in the same Neo4j database as distinct namespaces.

Suggested prefix:
- `P*` for broad Pacha canon
- or `PP*` for Pacha’s Pajamas-specific structures

Example:
- `PCharacter`
- `PStory`
- `PTheme`
- `PArtifact`
- `PBiome`

---

## 3. Design Principles

1. Model **story reality**, not generic note-taking.
2. Separate **canon concepts** from **source evidence**.
3. Preserve the duality of **waking world** and **dream world**.
4. Support multiple age bands and format variants.
5. Keep **pajamas, portals, festival, songs, and biomes** as first-class entities.
6. Allow later ingestion from books, scripts, decks, and scene outlines.

---

## 4. World Layers

### A. Story Reality Layer
The canonical ontology.

**Core node labels**
- `PCharacter`
- `PCharacterAspect`
- `PGroup`
- `PRealm`
- `PLocation`
- `PBiome`
- `PPortal`
- `PArtifact`
- `PArc`
- `PStory`
- `PScene`
- `PConflict`
- `PQuest`
- `PTransformation`
- `PTheme`
- `PSymbol`
- `PSong`
- `PPerformance`
- `PRitual`
- `PWakingIssue`

### B. Evidence Layer
For provenance and extraction.

**Core node labels**
- `PSource`
- `PChunk`
- `PClaim`

### C. Analysis / Continuity Layer
For development work, not canon.

**Optional node labels**
- `PNote`
- `PObservation`
- `PHypothesis`
- `PContinuityIssue`

---

## 5. Core Node Definitions

### `PSource`
A source artifact used for extraction (book, script, deck, outline, etc.).

**Properties**
- `id` (e.g. `pacha:source:book/toddler-tale`)
- `title`
- `source_type` (`book`, `script`, `deck`, `outline`, `treatment`, `notes`, `transcript`, `draft`)
- `author`
- `publisher`
- `path`
- `url`
- `source_date`
- `ingested_at`
- `summary`
- `canon_status` (`canon`, `draft`, `reference`, `superseded`)

---

### `PChunk`
A paragraph, page span, quote, summary, lyric, or scene excerpt from a Pacha source.

**Properties**
- `id` (e.g. `pacha:chunk:<source_id>/<hash>`)
- `text`
- `chunk_type` (`paragraph`, `excerpt`, `summary`, `quote`, `lyric`, `scene_excerpt`, `section`)
- `section_title`
- `page_start`
- `page_end`
- `source_date`
- `created_at`

---

### `PClaim`
A normalized proposition extracted from one or more chunks (character fact, event, relationship, theme mention).

**Properties**
- `id`
- `statement`
- `claim_type` (`character_fact`, `event`, `relationship`, `theme`, `setting`, `symbol`, `contradiction`)
- `confidence` (0–1)
- `status` (`draft`, `reviewed`, `contested`, `accepted`)

---

### `PCharacter`
Any named human, animal, plant, fungus, ancestor, guide, villain, or collective being.

**Examples**
- Pacha
- Paco
- Mama
- Papa
- Abuelita / Dr. Goldenberry
- Jag
- Hum
- Plat
- Wilder
- Pebble
- Tree / Ceiba
- Mushroom
- Mr. Tick
- Emperor Hamburgoni

**Properties**
- `name`
- `character_type` (`human`, `animal`, `plant`, `fungus`, `ancestor`, `guide`, `villain`, `collective`, `other`)
- `world_mode` (`waking`, `dream`, `both`)
- `description`
- `age_band` (for audience targeting)
- `traits` (array)
- `canon_status` (`canon`, `draft`, `reference`)

---

### `PCharacterAspect`
A symbolic or alternate manifestation of a character.

**Use for**
- dream persona
- symbolic double
- performance form
- age-shifted version

**Properties**
- `name`
- `aspect_type`
- `description`

---

### `PGroup`
A family, alliance, species cluster, movement, or villain network.

**Examples**
- Team Pacha
- New Food Order
- festival performers
- family unit

**Properties**
- `name`
- `group_type`
- `description`

---

### `PRealm`
A broad reality domain.

**Examples**
- waking world
- dream world
- nightmare zone
- Foodlandia

**Properties**
- `name`
- `realm_type`
- `description`

---

### `PLocation`
A recurring place or setting.

**Examples**
- Pacha’s home
- PACHA JAMMA stadium
- Amazon rainforest
- beach stage
- forest stage
- seed bank

**Properties**
- `name`
- `location_type` (`home`, `venue`, `biome_zone`, `realm_landmark`, `portal_site`, `other`)
- `description`
- `world_mode` (`waking`, `dream`, `both`)
- `risk_level` (optional, for threat/stakes)

---

### `PBiome`
A first-class ecological zone in the world model.

**Examples**
- wetlands
- mountain
- savannah
- desert
- forest
- farm
- jungle
- ocean
- arctic

**Properties**
- `name`
- `description`
- `elemental_affinity`
- `status`

---

### `PPortal`
A transition mechanism between states or worlds.

**Examples**
- pajama portal
- sleep transition
- shimmering dream passage

**Properties**
- `name`
- `portal_type`
- `description`
- `activation_condition`

---

### `PArtifact`
A meaningful object with narrative or symbolic function.

**Examples**
- magical pajamas
- mask
- chest
- key
- seed bank
- performance mic

**Properties**
- `name`
- `artifact_type` (`object`, `portal_key`, `symbol`, `tool`, `costume`, `other`)
- `description`
- `magical` (boolean)
- `world_mode` (`waking`, `dream`, `both`)

---

### `PArc`
A major multi-story arc.

**Examples**
- By Nature arc
- recurring dream progression
- PACHA JAMMA unification arc
- anti-extractive resistance arc

**Properties**
- `name`
- `description`
- `arc_type`
- `status`

---

### `PStory`
A discrete story unit.

**Examples**
- *A Toddler Tale Told By Nature*
- *A Tale Told By Nature*
- *The Magical Pajamas*
- *Foodlandia*
- *Plastic Island*

**Properties**
- `name`
- `story_type`
- `audience_range`
- `description`
- `canon_status`

---

### `PScene`
A beat, sequence, or scene.

**Properties**
- `id`
- `name`
- `scene_type`
- `summary`
- `order_index`

---

### `PConflict`
A threat, pressure, obstacle, or opposition force.

**Examples**
- stage fright
- bullying
- environmental destruction
- plastic pollution
- dream suppression
- parasitic takeover

**Properties**
- `name`
- `conflict_type`
- `description`
- `stakes`

---

### `PQuest`
A goal-directed mission.

**Examples**
- organize PACHA JAMMA
- recover seeds
- unite species
- save a biome
- reveal true identity

**Properties**
- `name`
- `description`
- `quest_type`
- `outcome_status`

---

### `PTransformation`
A meaningful change in a character, relationship, or world-state.

**Examples**
- fear to courage
- hidden self to revealed self
- isolation to belonging
- fragmentation to unity

**Properties**
- `name`
- `description`
- `transformation_type`

---

### `PTheme`
A recurring thematic strand.

**Examples**
- We Are ALL Connected
- every being has purpose
- remembrance
- ecological kinship
- belonging
- courage

**Properties**
- `name`
- `description`
- `theme_class`

---

### `PSymbol`
A recurring motif or image.

**Examples**
- magical pajamas
- mask
- portal
- rainbow
- seed
- chest and key

**Properties**
- `name`
- `description`
- `symbol_type`

---

### `PSong`
A named song or lyric motif.

**Examples**
- We Are ALL Connected
- PACHA JAMMA song
- Connected Dance

**Properties**
- `name`
- `description`
- `song_type`
- `mood`

---

### `PPerformance`
A staged expression inside the story world.

**Examples**
- opening festival act
- biome stage performance
- dance finale
- spoken-word performance

**Properties**
- `name`
- `performance_type`
- `description`
- `audience_scope`

---

### `PRitual`
A repeated, ceremonial, or meaning-bearing action.

**Examples**
- putting on the pajamas
- putting on the mask
- connected dance
- species gathering

**Properties**
- `name`
- `description`
- `ritual_type`

---

### `PWakingIssue`
A waking-life challenge mirrored by the dream story.

**Examples**
- fear of crowds
- asthma
- bullying
- exclusion
- environmental concern
- unhealthy food systems

**Properties**
- `name`
- `issue_type`
- `description`

---

## 6. Recommended Relationships

### Evidence
- `(:PSource)-[:CONTAINS]->(:PChunk)`
- `(:PChunk)-[:SUPPORTS]->(:PClaim)`
- `(:PChunk)-[:CONTRADICTS]->(:PClaim)`
- `(:PClaim)-[:ABOUT]->(:PCharacter)`
- `(:PClaim)-[:ABOUT]->(:PLocation)`
- `(:PClaim)-[:ABOUT]->(:PTheme)`
- `(:PClaim)-[:ABOUT]->(:PStory)`

### Character / Identity
- `(:PCharacter)-[:MEMBER_OF]->(:PGroup)`
- `(:PCharacter)-[:ALLY_OF]->(:PCharacter)`
- `(:PCharacter)-[:OPPOSES]->(:PCharacter)`
- `(:PCharacter)-[:GUIDES]->(:PCharacter)`
- `(:PCharacter)-[:MENTORS]->(:PCharacter)`
- `(:PCharacter)-[:FAMILY_OF]->(:PCharacter)`
- `(:PCharacter)-[:HAS_ASPECT]->(:PCharacterAspect)`
- `(:PCharacter)-[:DREAM_MIRROR_OF]->(:PCharacter)`

### World / Setting
- `(:PRealm)-[:CONTAINS]->(:PLocation)`
- `(:PLocation)-[:WITHIN_BIOME]->(:PBiome)`
- `(:PPortal)-[:CONNECTS]->(:PRealm)`
- `(:PArtifact)-[:OPENS]->(:PPortal)`
- `(:PArtifact)-[:BELONGS_TO]->(:PCharacter)`
- `(:PArtifact)-[:SYMBOLIZES]->(:PTheme)`

### Plot / Structure
- `(:PArc)-[:CONTAINS_STORY]->(:PStory)`
- `(:PStory)-[:HAS_SCENE]->(:PScene)`
- `(:PStory)-[:CENTERS_ON]->(:PQuest)`
- `(:PStory)-[:FEATURES_CONFLICT]->(:PConflict)`
- `(:PStory)-[:RESULTS_IN]->(:PTransformation)`
- `(:PScene)-[:OCCURS_IN]->(:PLocation)`
- `(:PScene)-[:INVOLVES]->(:PCharacter)`
- `(:PCharacter)-[:UNDERTAKES]->(:PQuest)`
- `(:PConflict)-[:THREATENS]->(:PLocation)`
- `(:PConflict)-[:THREATENS]->(:PCharacter)`
- `(:PCharacter)-[:CAUSES]->(:PConflict)`
- `(:PTransformation)-[:CHANGES]->(:PCharacter)`
- `(:PTransformation)-[:CHANGES]->(:PGroup)`

### Theme / Expression
- `(:PSymbol)-[:EXPRESSES]->(:PTheme)`
- `(:PSong)-[:EXPRESSES]->(:PTheme)`
- `(:PPerformance)-[:PERFORMED_BY]->(:PCharacter)`
- `(:PPerformance)-[:STAGED_AT]->(:PLocation)`
- `(:PSong)-[:FEATURED_IN]->(:PPerformance)`
- `(:PRitual)-[:PERFORMED_IN]->(:PScene)`
- `(:PRitual)-[:EXPRESSES]->(:PTheme)`

### Waking / Dream Mirror
- `(:PStory)-[:MIRRORS]->(:PWakingIssue)`
- `(:PWakingIssue)-[:RESOLVED_THROUGH]->(:PTransformation)`
- `(:PScene)-[:ECHOES]->(:PWakingIssue)`

---

## 7. Minimal Viable Schema

Start with:

- `PSource`
- `PChunk`
- `PClaim`
- `PCharacter`
- `PGroup`
- `PRealm`
- `PLocation`
- `PBiome`
- `PArtifact`
- `PStory`
- `PScene`
- `PConflict`
- `PQuest`
- `PTransformation`
- `PTheme`
- `PSong`

This is enough to represent:
- who exists
- where they act
- what threatens the world
- what quest is underway
- how dream and waking life connect
- what message the story carries

---

## 8. Recommended Neo4j Constraints

```cypher
CREATE CONSTRAINT p_source_id IF NOT EXISTS
FOR (n:PSource) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT p_chunk_id IF NOT EXISTS
FOR (n:PChunk) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT p_claim_id IF NOT EXISTS
FOR (n:PClaim) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT p_character_name IF NOT EXISTS
FOR (n:PCharacter) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_group_name IF NOT EXISTS
FOR (n:PGroup) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_realm_name IF NOT EXISTS
FOR (n:PRealm) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_location_name IF NOT EXISTS
FOR (n:PLocation) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_biome_name IF NOT EXISTS
FOR (n:PBiome) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_artifact_name IF NOT EXISTS
FOR (n:PArtifact) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_story_name IF NOT EXISTS
FOR (n:PStory) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_theme_name IF NOT EXISTS
FOR (n:PTheme) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_song_name IF NOT EXISTS
FOR (n:PSong) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT p_scene_id IF NOT EXISTS
FOR (n:PScene) REQUIRE n.id IS UNIQUE;
```

---

## 9. Integration with agent-lab

- **Same Neo4j**: Pacha nodes (P*) and meta-layer nodes (ML*) coexist. No shared world-model labels.
- **Shared ingestion**: A Pacha book can be ingested as `MLSource`/`MLChunk` (general pipeline) and/or `PSource`/`PChunk` (Pacha-specific). Routing depends on the ingestion script.
- **Analysis layer**: Dream, Insight, Idea, Theme, etc. are **not** meta-layer and can attach to content from either world. Pacha dreams map to both `Dream` (analysis) and `PStory`/`PScene` (Pacha canon).
- **Prefix convention**: Use `pacha:` in `id` fields (e.g. `pacha:source:book/tale`) so namespacing is explicit.

---

## 10. Example World Spine

```text
Pacha (PCharacter)
  FAMILY_OF -> Mama
  FAMILY_OF -> Papa
  FAMILY_OF -> Paco
  MENTORS <- Abuelita / Dr. Goldenberry
  UNDERTAKES -> Organize PACHA JAMMA

Magical Pajamas (PArtifact)
  BELONGS_TO -> Pacha
  OPENS -> Dream Portal
  SYMBOLIZES -> Interconnectedness

Dream World (PRealm)
  CONTAINS -> PACHA JAMMA Stadium
  CONTAINS -> Amazon Rainforest

Jag (PCharacter)
  GUIDES -> Pacha

Mr. Tick (PCharacter)
  OPPOSES -> Pacha
  CAUSES -> Dream Suppression

A Tale Told By Nature (PStory)
  CENTERS_ON -> Organize PACHA JAMMA
  FEATURES_CONFLICT -> Hidden Identity
  RESULTS_IN -> Self-Revelation
  MIRRORS -> Fear of Belonging
```

