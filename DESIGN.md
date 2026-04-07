# RPG Session Notes → Wiki: Design Document

A system for extracting structured knowledge from role-playing game session notes and generating Wikipedia-style articles about the fictional world.

## The Problem

Long-running tabletop RPG campaigns accumulate vast amounts of lore spread across dozens or hundreds of session notes. Players and GMs want to:

- Look up facts about characters, locations, and events
- Track what's known vs. suspected vs. rumored
- See when information was learned (which session)
- Maintain a living reference that grows with the campaign

Manually maintaining a wiki is tedious and falls out of sync. This system uses LLMs to extract structured facts from session notes and mechanically aggregate them into entity-specific files that can be rendered as wiki articles.

## Design Principles

### Separation of Concerns

The pipeline has six distinct phases with clear boundaries:

1. **Extract (LLM)**: Session notes → structured facts + pass-through resolution
2. **Resolve (editable)**: Maps extracted entity_ids to resolved entity_ids
3. **Split (mechanical)**: Resolved extraction → per-entity-per-session data files
4. **Register (mechanical)**: Resolved extraction → updated entity registry
5. **Merge (mechanical)**: Entity-session files → per-entity data files
6. **Render (LLM)**: Entity data → wiki articles (on-demand generation)

This separation means:
- Session extractions are immutable snapshots with full provenance
- Resolution files enable correcting entity_id mistakes without re-extraction
- Entity-session files capture each entity's data from one session
- Entity data files can be regenerated at any time by merging entity-session files
- Articles can be re-rendered with different styles without re-extraction

### Facts as Source of Truth

Rather than treating wiki articles as the source of truth (editing them in place), we store individual facts with full provenance. Articles are *generated views* of the fact database.

This enables:
- Querying facts directly ("what did we learn in sessions 20-30?")
- Regenerating articles with different templates
- Handling contradictions explicitly
- Full auditability of where information came from

### Version Control as Foundation

All files — inputs, intermediate outputs, and final articles — live in a git repository. This provides:
- History and rollback for non-deterministic LLM outputs
- Collaboration and review workflows
- Provenance tracking (each extraction records the registry commit it used)
- First-class support for manual edits (just commit them with a message)

### Separate Tool and Data Repositories

The wikify tool and the campaign data live in separate git repositories. This separation ensures that commits have a single meaning:

- **Tool repository (wikify)**: Code changes, prompt improvements, build system updates
- **Data repository (aral)**: Session notes, extractions, registry edits, rendered articles

Without this separation, the commit history mixes unrelated concerns—a code refactor appears alongside a session extraction, making it harder to understand the evolution of either.

The `registry_commit` field in extractions references the data repository's history, providing accurate provenance tracking independent of tool version.

**Current implementation**: The data repository is mounted as a git submodule at `data/`. This is a temporary measure that simplifies development by keeping both repos in a single working directory.

**Future direction**: The tool should support a configurable reference to an external data repository (via environment variable, CLI argument, or config file). This would allow:
- Using the same wikify installation with multiple campaigns
- Deploying wikify as a standalone tool without bundled data
- Cleaner separation with no submodule complexity

### Incremental Updates

The system is designed for ongoing campaigns. After each session:
1. Extract facts from the new session
2. Re-run aggregation (fast, mechanical)
3. Regenerate affected articles

No need to reprocess the entire corpus for routine updates.

---

## Data Model

### Directory Structure

```
/wiki
  /sessions/
    /raw/                    # Original session notes (input)
      session-001.txt
      session-002.txt
    /context/                # Optional context hints (input)
      session-007.txt        # Only sessions needing disambiguation
    /extracted/              # LLM-extracted facts
      session-001.json
      session-002.json
    /resolver/               # Entity ID resolution (editable)
      session-001.json       # Maps extracted IDs → resolved IDs
      session-002.json
  /entities/
    /sessions/               # Per-entity-per-session data (generated)
      /session-001/
        baron-aldric.json
        thornwood.json
      /session-002/
        baron-aldric.json
        the-sunken-library.json
    /data/                   # Aggregated facts per entity (generated)
      baron-aldric.json
      thornwood.json
    /articles/               # Wiki articles (generated)
      baron-aldric.md
      thornwood.md
  entity-registry.json       # Master list of entities and aliases
  SConstruct                 # Build configuration
```

### Session Extraction Format

Each `/sessions/extracted/session-{NNN}.json`:

```json
{
  "session_number": 12,
  "extracted_at": "2025-02-25T14:30:00Z",
  "registry_commit": "a1b2c3d4",
  "extractor_version": "1.0.0",

  "context_resolutions": {
    "the mountain": "Mount Tambora",
    "the baron": "Baron Aldric"
  },

  "entities": [
    {
      "canonical_name": "Baron Aldric",
      "aliases": ["Aldric"],
      "type": "person",
      "is_new": false
    },
    {
      "canonical_name": "The Sunken Library",
      "aliases": [],
      "type": "location",
      "is_new": true
    }
  ],

  "facts": [
    {
      "subject_entity": "Baron Aldric",
      "object_entities": ["King Aldren"],
      "text": "Served as court wizard to King Aldren before his exile",
      "category": "history",
      "confidence": "stated"
    },
    {
      "subject_entity": "Baron Aldric",
      "object_entities": [],
      "text": "Can cast illusions powerful enough to fool multiple people simultaneously",
      "category": "abilities",
      "confidence": "observed"
    },
    {
      "subject_entity": "The Sunken Library",
      "object_entities": ["Lake Veris"],
      "text": "Located beneath Lake Veris, accessible only at low water",
      "category": "geography",
      "confidence": "stated"
    }
  ]
}
```

The `registry_commit` field records which version of the entity registry was used for this extraction, enabling full provenance tracking.

### Session Resolution Format

Each `/sessions/resolver/session-{NNN}.json`:

```json
{
  "session_number": 12,
  "generated_at": "2025-02-25T14:30:00Z",
  "resolutions": {
    "baron-aldric": "baron-aldric",
    "king-aldren": "king-aldren",
    "the-sunken-library": "the-sunken-library",
    "lake-veris": "lake-veris"
  }
}
```

Resolution files are generated automatically during extraction as pass-through mappings (each entity_id maps to itself). They can be edited to:

- **Correct typos**: `"baron-aldrich": "baron-aldric"` — fix misspellings
- **Merge duplicates**: `"mont-tambora": "mount-tambora"` — consolidate entities the LLM extracted with different IDs
- **Exclude non-entities**: `"the-party": null` — remove items that shouldn't be tracked as entities

N.B. **Missing keys**: Every `entity_id` in the extraction must have a corresponding key; use `null` to intentionally exclude an `entity_id`.

When split/register runs, it loads both the extraction and resolution files, translating all entity_ids through the resolution before processing. This enables correcting extraction mistakes without re-running the LLM.

Resolution values:
- **Same as key**: Pass-through, no change (default)
- **Different string**: Remap to a different entity_id
- **null**: Exclude this entity from aggregation entirely

### Fact Schema

Each fact has:

| Field | Required | Description |
|-------|----------|-------------|
| `subject_entity` | Yes | The canonical name of the entity this fact is primarily about |
| `object_entities` | No | List of other canonical entity names referenced by the fact |
| `text` | Yes | The fact itself, as a complete statement |
| `category` | Yes | What aspect of the subject this describes |
| `confidence` | Yes | How reliable this information is (see below) |

### Confidence Categories

| Label | Meaning | Example |
|-------|---------|---------|
| `stated` | Explicitly said by narrator/GM as true | "The Baron is 50 years old" |
| `observed` | Directly witnessed by player characters | "The Baron cast a fireball" |
| `character_claim` | Stated by an NPC (may be unreliable) | "The innkeeper says the Baron was framed" |
| `implied` | Reasonably inferred from events | "The Baron knew the password, suggesting prior familiarity" |
| `rumor` | Secondhand, hearsay, in-world reputation | "Villagers say the Baron murdered his brother" |
| `player_theory` | Out-of-character player speculation | "The party suspects the Baron is planning to betray them" |
| `uncertain` | Ambiguous, possibly misunderstood | "A figure matching the Baron's description was seen fleeing" |
| `superseded` | Contradicted by later information | (Added during aggregation, not extraction) |

These categories were chosen because they:
1. Map to distinctions actually present in session notes (dialogue vs. narration vs. inference)
2. Are reliably distinguishable by an LLM (unlike numerical confidence scores)
3. Are useful for article generation (different phrasing for stated facts vs. rumors)
4. Are appropriate for RPG contexts (GM narration, NPC dialogue, PC observation, town gossip, player theorizing)

### Entity Registry Format

`entity-registry.json`:

```json
{
  "entities": {
    "baron-aldric": {
      "canonical_name": "Baron Aldric",
      "aliases": ["Aldric", "Baron Aldric von Stein"],
      "type": "person",
      "first_appearance": 3
    },
    "thornwood": {
      "canonical_name": "Thornwood",
      "aliases": ["Thornwood Village"],
      "type": "location",
      "first_appearance": 1
    }
  }
}
```

### Session Entity Facts Format (Intermediate)

Each `/entities/sessions/session-{NNN}/{entity-id}.json`:

```json
{
  "entity_id": "baron-aldric",
  "facts": [
    {
      "text": "Served as court wizard to King Aldren before his exile",
      "category": "history",
      "confidence": "stated",
      "source_session": 12,
      "object_entities": ["king-aldren"]
    }
  ],
  "referenced_by": [
    {
      "source_entity": "the-sunken-library",
      "fact_text": "Baron Aldric is searching for a tome hidden in the library",
      "source_session": 12
    }
  ]
}
```

These files contain only facts and references — no entity metadata. Entity metadata (`canonical_name`, `aliases`, `type`, `first_appearance`) is retrieved from the registry during merge.

### Aggregated Entity Format

Each `/entities/data/{entity-id}.json`:

```json
{
  "entity_id": "baron-aldric",
  "canonical_name": "Baron Aldric",
  "aliases": ["Aldric", "Baron Aldric von Stein"],
  "type": "person",
  "first_appearance": 3,

  "facts": [
    {
      "text": "First appeared in Thornwood seeking mercenaries",
      "category": "history",
      "confidence": "stated",
      "session": 3,
      "object_entities": ["Thornwood"]
    },
    {
      "text": "Served as court wizard to King Aldren before his exile",
      "category": "history",
      "confidence": "stated",
      "session": 12,
      "object_entities": ["King Aldren"]
    }
  ],

  "referenced_by": [
    {
      "entity": "the-sunken-library",
      "entity_name": "The Sunken Library",
      "text": "Baron Aldric is searching for a tome hidden in the library",
      "session": 12
    }
  ],

  "sessions_appeared": [3, 12, 15, 23],
  "last_updated": "2025-02-25T14:35:00Z"
}
```

The `referenced_by` section captures facts from *other* entities where this entity appears in `object_entities`. This enables bidirectional relationship discovery without duplicating facts.

---

## Build System

The pipeline is managed by SCons, which handles dependency tracking and incremental rebuilds.

### Why SCons?

SCons was chosen over Make because:
- Native Python — builders are Python functions, matching the rest of the tooling
- Content-based change detection (MD5) rather than just timestamps
- Better handling of dynamic dependencies through custom scanners
- No need for a separate dependency-generation phase

### Dependency Graph

```
                                    ┌──────────────────┐
                                    │ entity-registry  │
                                    │     (input)      │
                                    └────────┬─────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                                   │                                   │
         ▼                                   ▼                                   ▼
┌─────────────────┐               ┌─────────────────┐               ┌─────────────────┐
│ session-001.txt │               │ session-002.txt │               │ session-003.txt │
└────────┬────────┘               └────────┬────────┘               └────────┬────────┘
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌─────────────────┐               ┌─────────────────┐               ┌─────────────────┐
│session-001.json │               │session-002.json │               │session-003.json │
│ + resolver/     │               │ + resolver/     │               │ + resolver/     │
└────────┬────────┘               └────────┬────────┘               └────────┬────────┘
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌─────────────────┐               ┌─────────────────┐               ┌─────────────────┐
│ entities/       │               │ entities/       │               │ entities/       │
│ sessions/       │               │ sessions/       │               │ sessions/       │
│ session-001/    │               │ session-002/    │               │ session-003/    │
│   *.json        │               │   *.json        │               │   *.json        │
└────────┬────────┘               └────────┬────────┘               └────────┬────────┘
         │                                 │                                 │
         └─────────────────────────────────┼─────────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
          ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
          │ entities/data/  │    │ entities/data/  │    │ entities/data/  │
          │ baron-aldric    │    │ thornwood.json  │    │ king-aldren     │
          └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
                   │                      │                      │
                   ▼                      ▼                      ▼
          ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
          │ baron-aldric.md │    │  thornwood.md   │    │ king-aldren.md  │
          └─────────────────┘    └─────────────────┘    └─────────────────┘
```

Note: Resolution files (`resolved/session-NNN.json`) are generated during extraction as
pass-through mappings. They can be edited to correct entity_id mistakes. Changes to
resolution files trigger rebuild of split/register/merge for that session.

### The Registry Dependency

Extraction requires the entity registry to resolve references to existing entities. This creates a potential circular dependency: extraction reads from the registry, but new entities discovered during extraction should be added to the registry.

We break this cycle with the following rule:

**Extraction can only run against a committed, clean registry.**

Before extraction runs, the build system verifies that the working tree copy of `entity-registry.json` matches HEAD (no uncommitted changes). Each extraction output records the git commit SHA of the registry used.

This approach:
- Eliminates ambiguity about which registry version was used
- Makes manual registry edits first-class (edit, commit with a message, then extract)
- Enables provenance tracking across the entire history
- Forces intentionality — you can't accidentally extract against a half-edited registry

### Sequential Extraction

Sessions must be extracted in order. Session N's extraction benefits from having entities discovered in sessions 1 through N-1 already in the registry.

This means:
- New session extraction is fast (just extract the new session)
- Re-extraction of an old session doesn't *invalidate* later extractions (they remain valid snapshots)
- Re-extraction is a choice driven by cost/benefit, not a dependency requirement

### Build Targets

| Builder | Input | Output | Notes |
|---------|-------|--------|-------|
| `ExtractSession` | `session-NNN.txt` + registry | `session-NNN.json` + `resolved/session-NNN.json` | LLM call, sequential |
| `SplitSession` | `session-NNN.json` + `resolved/session-NNN.json` | `entities/sessions/session-NNN/*.json` | Mechanical, outputs SessionEntityFacts |
| `RegisterEntities` | `session-NNN.json` + `resolved/session-NNN.json` | `entity-registry.json` | Mechanical, updates registry |
| `MergeEntity` | `entities/sessions/*/entity-id.json` + registry | `entities/data/entity-id.json` | Mechanical, outputs EntityData |
| `RenderArticle` | `entity-name.json` | `entity-name.md` | LLM call, parallel |

### Build Commands

```bash
# Normal workflow: extract new sessions, aggregate, render
scons

# Re-extract from a specific session onward (after registry improvements)
scons extract --from=20

# Re-extract everything (after prompt improvements)
scons extract --all

# Rebuild aggregation and articles only (no extraction)
scons aggregate
scons render
```

### When to Re-Extract

Re-extraction is expensive because it requires a capable inference engine. It makes sense when:

- You've manually corrected the registry (merged entities, fixed aliases) and want earlier sessions to benefit from better entity resolution
- You've improved the extraction prompt
- You've found errors in an extraction that need correction

Note that re-extraction of session N doesn't *require* re-extraction of sessions before or after it. Each extraction is a valid snapshot relative to the registry version it used. Re-extraction is always an *opportunity* for improvement, not a *requirement* driven by dependency invalidation.

---

## Key Design Decisions

### Why JSON Files Instead of a Database?

Options considered:
1. **JSON files** — Simple, human-readable, git-friendly
2. **SQLite** — Query capability, handles scale, still portable
3. **Hybrid** — SQLite for storage, JSON exports for LLM consumption

We chose **JSON files** because:
- Session extractions are write-once, read-many
- The aggregation step is a full rebuild anyway
- Git versioning provides history and collaboration
- No dependencies beyond a JSON parser
- Human-inspectable for debugging
- Disk space is cheap

The tradeoff is losing ad-hoc query capability, but for most campaigns (hundreds of entities, thousands of facts), full-scan is fast enough.

### Why Not Unify Facts and Relationships?

Early designs had a separate `relationships` array:

```json
"relationships": [
  {
    "entity_1": "Baron Aldric",
    "entity_2": "King Aldren",
    "relationship": "served"
  }
]
```

This was rejected because:
- It duplicates information already in facts
- The relationship label ("served") loses nuance present in the fact text ("served as court wizard before his exile")
- Multi-entity facts (A negotiated between B and C) are awkward to represent
- Relationships are just facts that reference other entities

Instead, facts have an optional `object_entities` list. Relationships emerge from queries: "find all facts where X is subject and Y is in object_entities."

We also considered adding `relationship_type` labels to facts, but decided against it. The ontology we're generating isn't that structured, and the free-text fact captures nuance that labels would flatten.

### Why Not Store Contextual Aliases?

Session notes often use contextual references: "the mountain," "the baron," "the sword." These can't be stored as global aliases because they're session-scoped — "the mountain" means Mount Tambora in sessions 4-9 but might mean Mount Kira in sessions 30-35.

Options considered:
1. **Don't store contextual aliases** — Only store globally unambiguous aliases
2. **Session-scoped resolution tables** — Store how contextual references resolved in each session
3. **Scoped aliases in registry** — Store aliases with session-range metadata

We chose **Option 2**: Each session extraction includes a `context_resolutions` block documenting how contextual references were resolved. This is for auditability only — all facts use canonical names, so aggregation remains unambiguous.

The extraction prompt instructs the LLM to:
- Resolve contextual references using session context
- Output facts using only canonical entity names
- Only add aliases that would unambiguously identify this entity across the entire campaign

### Why Natural Language Confidence Labels?

Options considered:
1. **Numerical scores (0-100)** — Maximum granularity
2. **Natural language categories** — Discrete, meaningful buckets

We chose **natural language categories** because LLMs don't have well-calibrated numerical probability estimates. When asked for confidence scores:
- They cluster around arbitrary anchors (70, 80, 90)
- They're inconsistent across runs
- They provide false precision (what's the difference between 73 and 76?)

Natural language categories map to distinctions the LLM can actually identify from text:
- "A character explicitly stated this" — the LLM can identify dialogue
- "This is implied by events" — the LLM can recognize inference
- "This is speculation by characters" — the LLM can distinguish opinions from facts

The categories are essentially a text classification task, which LLMs do reliably.

### Handling New Entities

When extraction identifies a new entity, two approaches were considered:

**Auto-add**: Automatically add to registry. Faster, but risks creating duplicate entities for the same thing ("the Old Library" in session 8 might be the same as "the library" in session 12).

**Queue for review**: Add to a pending list for human review. Safer for entity resolution.

The implemented approach is auto-add via the Register phase: new entities are automatically merged into the registry during aggregation. This enables sequential extraction to benefit from previously discovered entities. Periodically review the registry for duplicates that should be merged. Entity merging is straightforward: update the registry, re-run aggregation, and the facts automatically consolidate.

### Handling Contradictions

Information in RPGs gets retconned, misremembered, or deliberately falsified by NPCs. Rather than silently overwriting facts, the system preserves history:

- Both facts are kept in the entity file
- The older fact can be marked with `"superseded_by": {session_number}` during a manual review pass
- The article generator can phrase contradictions narratively: "Originally believed to be from the Northern Kingdoms [S5], though later revealed to be Eldarian [S23]"

---

## Pipeline Details

### Phase 1: Extraction

**Input**: Raw session notes + entity registry

**Process**: LLM extracts structured facts, resolving contextual references

**Output**:
- Session extraction JSON file with provenance metadata
- Pass-through resolution file (generated as side effect)

The extraction prompt provides the current entity registry (canonical names and aliases) so the LLM can resolve references to existing entities. New entities are flagged with `is_new: true`.

The extraction must run against a clean, committed registry. The output records:
- `registry_commit`: Git SHA of the registry used
- `extractor_version`: Version of the extraction prompt/tooling
- `extracted_at`: Timestamp

The extraction builder also generates a pass-through resolution file at `sessions/resolver/session-{NNN}.json`. This file maps each entity_id to itself (identity mapping) and can be edited to correct mistakes without re-extraction.

### Phase 2a: Split

**Input**: Session extraction file + resolution file

**Process**: Mechanical split (no LLM)

**Output**: Per-entity-per-session data files in `entities/sessions/session-NNN/`

The split step first loads both the extraction and resolution files, producing a `ResolvedExtraction` with all entity_ids translated through the resolution. This enables correcting entity_id mistakes without re-extraction.

For each entity referenced in the resolved extraction's facts (as subject or object):
1. Collect facts where `subject_entity` matches the entity
2. Collect `referenced_by` entries from facts where this entity appears in `object_entities`
3. Write entity-session file as `entities/sessions/session-NNN/{entity-id}.json`

Each entity-session file contains a `SessionEntityFacts` object — just facts and references, no entity metadata. This means split doesn't need access to the registry and naturally handles facts about entities that already exist.

Resolution translation:
- If resolution maps `old-id` → `new-id`, facts use `new-id` and file is named `new-id.json`
- If resolution maps `id` → `null`, the entity is excluded from split output
- If multiple extracted IDs resolve to the same target, their entities are merged (aliases combined, min first_appearance)
- If an entity_id is missing from the resolution map, aggregation fails with `KeyError`

### Phase 2b: Register

**Input**: Session extraction file + resolution file

**Process**: Mechanical registry update (no LLM)

**Output**: Updated `entity-registry.json`

The register step first loads both the extraction and resolution files, producing a `ResolvedExtraction` with all entity_ids translated through the resolution.

For each entity discovered in the resolved extraction:
1. If the resolved entity_id is new, add it to the registry
2. If the resolved entity_id exists, merge the new data (union aliases, use minimum first_appearance)

This enables "Session N benefits from entities discovered in sessions 1 through N-1" by automatically propagating discovered entities to the registry. Resolution ensures that corrected entity_ids are registered under their canonical form.

### Phase 2c: Merge

**Input**: All entity-session files for a given entity + entity registry

**Process**: Mechanical merge (no LLM)

**Output**: Per-entity data file in `entities/data/`

For each entity in the registry:
1. Load entity metadata from the registry (`canonical_name`, `aliases`, `type`, `first_appearance`)
2. Collect all `entities/sessions/*/entity-id.json` files (`SessionEntityFacts`)
3. Validate all session files are for the expected entity
4. Combine facts and references from all session files
5. Derive `sessions_appeared` from facts' `source_session` values
6. Write merged `EntityData` file

**Errors**:
- `EntityNotFoundError`: Raised if the entity_id is not in the registry
- `EntityMismatchError`: Raised if a session file contains data for a different entity

Both phases are fully deterministic and can be re-run any time. They're also fast — no LLM calls, just JSON parsing and restructuring.

The split/merge separation provides:
- **Granular intermediate artifacts**: Each entity-session file is inspectable
- **Explicit dependencies**: The build system tracks which sessions contribute to each entity
- **Easier debugging**: Trace any fact back to its specific session file
- **Single source of truth**: Entity metadata lives only in the registry, not duplicated in split files

### Phase 3: Rendering

**Input**: Entity data file

**Process**: LLM generates wiki-style article

**Output**: Markdown article with session citations

The rendering prompt specifies:
- Article structure and voice
- Citation format (e.g., `[S12]` for session 12)
- How to handle different confidence categories
- Whether to include player theories

Rendering is embarrassingly parallel — each entity can be rendered independently.

---

## Session Context Hints

When session notes use ambiguous contextual references, create a context file at `sessions/context/session-{NNN}.txt`. The extraction builder automatically checks for this file and inserts its contents into the prompt between "Known Entities" and "Session Notes".

Example context file:

```
This session takes place on Mount Tambora, referred to throughout as
"the mountain." The party is accompanied by Sera (the ranger from
session 5) and still carrying the Queensbane sword.
```

Context files are optional—if absent, extraction proceeds without a context section.

Natural language hints work better than structured formats (like YAML front-matter) because:
- They match the register of the session notes
- They handle nuance ("the Baron appears in disguise as Corwin")
- They don't require the LLM to switch parsing modes
- You can be partial — only hint what's genuinely ambiguous

---

## Future Considerations

### Entity Merging

When two entities are discovered to be the same, there are two approaches:

**Via Resolution (no registry change)**:
1. Edit resolution files for affected sessions: `"old-entity-id": "canonical-entity-id"`
2. Re-run aggregation (facts consolidate under the canonical entity)
3. Re-render affected articles

This preserves the original extractions and doesn't require updating the registry.

**Via Registry (permanent change)**:
1. Update registry: merge aliases, keep one canonical name
2. Re-run aggregation (facts automatically consolidate under the surviving entity)
3. Re-render affected articles

Use resolution for ad-hoc corrections; use registry for permanent entity definitions.

### Category Expansion

The entity `type` field (person, location, object, organization, phenomenon) may need expansion. Add types as needed; the system doesn't depend on a fixed set.

### Confidence Upgrades

A fact might start as `player_theory` and later be confirmed as `stated`. This could be handled by:
- Adding a new fact with higher confidence (both remain in history)
- Manual annotation linking the theory to its confirmation
- A `confirmed_by` field on theory facts

### Player Theory Handling in Articles

Player theories (`player_theory` confidence) can be:
- **Included**: The wiki becomes a record of both world-state and party-state
- **Excluded**: The wiki is strictly in-world encyclopedia
- **Separate section**: Articles have a collapsible "Party Theories" section

This is a rendering-time decision and doesn't affect extraction or storage.

### Multi-Campaign Support

For shared universes or multiple campaign timelines:

```
/wiki
  /campaigns/
    /campaign-a/
      /sessions/
      /entities/
      entity-registry.json
    /campaign-b/
      /sessions/
      /entities/
      entity-registry.json
  /shared/
    entity-registry.json    # Cross-campaign entities
```

The shared registry could be referenced by campaign-specific extraction, enabling entities that appear in multiple campaigns to be tracked consistently.
