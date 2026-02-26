# CLAUDE.md - Aral Wiki Generator

This project extracts structured knowledge from RPG session notes and generates Wikipedia-style articles about the fictional world of Aral.

## Project Overview

A pipeline that:
1. **Extracts** facts from session notes using an LLM
2. **Aggregates** facts into per-entity data files (mechanical, no LLM)
3. **Renders** entity data into wiki articles using an LLM

All files are version-controlled. The build is managed by SCons.

## Repository Structure

```
aral/
  pipeline/
    models/           # Pydantic data models
      fact.py         # Fact, ConfidenceLevel
      entity.py       # Entity, EntityData  
      extraction.py   # ExtractionResult, ContextResolution
      registry.py     # Registry, AliasIndex
    
    extraction/       # Session → structured facts
      prompt.py       # build_extraction_prompt(session, registry) -> str
      parser.py       # parse_extraction_response(raw) -> ExtractionResult
      extract.py      # extract_session(session, registry, client) -> ExtractionResult
    
    aggregation/      # Extractions → per-entity data
      aggregate.py    # aggregate_entity(entity_id, extractions, registry) -> EntityData
    
    rendering/        # Entity data → markdown articles
      prompt.py       # build_render_prompt(entity_data) -> str
      parser.py       # parse_render_response(raw) -> str
      render.py       # render_article(entity_data, client) -> str
    
    llm/              # LLM client abstraction
      client.py       # LLMClient protocol, AnthropicClient
    
    git/              # Git integration
      registry.py     # verify_registry_clean() -> commit SHA or raises
    
    builders/         # SCons builders
      extraction.py
      aggregation.py
      rendering.py
  
  tests/
    conftest.py
    fixtures/
      sessions/       # Sample raw session texts
      extractions/    # Hand-written valid extraction JSONs
      registries/     # Sample registries
    models/
    extraction/
    aggregation/
    rendering/
  
  data/
    sessions/
      raw/            # Input: session-001.txt, session-002.txt, ...
      extracted/      # Output: session-001.json, session-002.json, ...
    entities/
      data/           # Output: baron-aldric.json, ...
      articles/       # Output: baron-aldric.md, ...
    entity-registry.json
  
  SConstruct
  README.md
```

## Data Model

### Fact

```python
class ConfidenceLevel(str, Enum):
    STATED = "stated"              # Explicitly said by narrator/GM
    OBSERVED = "observed"          # Directly witnessed by PCs
    CHARACTER_CLAIM = "character_claim"  # Stated by NPC (may be unreliable)
    IMPLIED = "implied"            # Reasonably inferred from events
    RUMOR = "rumor"                # Secondhand, hearsay
    PLAYER_THEORY = "player_theory"  # Out-of-character speculation
    UNCERTAIN = "uncertain"        # Ambiguous, possibly misunderstood
    SUPERSEDED = "superseded"      # Contradicted by later info

class Fact(BaseModel):
    subject_entity: str            # Canonical name of primary entity
    object_entities: list[str] = []  # Other entities referenced
    text: str                      # The fact itself
    category: str                  # history, abilities, geography, etc.
    confidence: ConfidenceLevel
```

### ExtractionResult

```python
class ExtractionResult(BaseModel):
    session_number: int
    extracted_at: datetime
    registry_commit: str           # Git SHA of registry used
    extractor_version: str
    
    context_resolutions: dict[str, str]  # "the mountain" -> "Mount Tambora"
    entities: list[ExtractedEntity]
    facts: list[Fact]
```

### Registry

```python
class Entity(BaseModel):
    canonical_name: str
    aliases: list[str]
    type: str                      # person, location, object, organization, phenomenon
    first_appearance: int          # Session number

class Registry(BaseModel):
    entities: dict[str, Entity]    # entity_id -> Entity
    alias_index: dict[str, str]    # lowercase alias -> entity_id
```

### EntityData (aggregated)

```python
class EntityData(BaseModel):
    entity_id: str
    canonical_name: str
    aliases: list[str]
    type: str
    first_appearance: int
    
    facts: list[AggregatedFact]    # Facts where this entity is subject
    referenced_by: list[Reference]  # Facts from other entities mentioning this one
    sessions_appeared: list[int]
    last_updated: datetime
```

## Build System

SCons manages the build. Key rules:

### Extraction requires clean registry

Before extraction runs, verify `entity-registry.json` matches HEAD:

```python
def get_registry_commit_sha("entity-registry.json") -> str:
    """Returns commit SHA if clean, raises if dirty or uncommitted."""
```

Each extraction records the registry commit in its output.

### Sequential extraction

Sessions must be extracted in order. Session N benefits from entities discovered in sessions 1 through N-1.

### Dependency flow

```
session-NNN.txt + registry → session-NNN.json (LLM)
all session-*.json → entity-*.json (mechanical)
entity-*.json → entity-*.md (LLM)
```

### Build commands

```bash
scons extract --session=20        # Extract from session-20.txt
scons aggregate                   # Rebuild aggregation only
scons render                      # Rebuild dirty articles only
scons render --article=thornwood  # Rebuild article even if not dirty
scons --session=20                # Extract indicated session, aggregate, render as needed
```

## Testing Strategy

### Aggregation (deterministic)

Full unit tests and property-based tests with Hypothesis:

- Order independence: same extractions in any order → identical output
- Idempotence: duplicate extractions don't duplicate facts
- Completeness: every fact with subject_entity=X appears in X's data
- Session list accuracy: sessions_appeared matches actual sessions

### Extraction/Rendering (LLM-dependent)

Test the seams, not the LLM:

- **Prompt builders**: Unit test that inputs produce expected prompt structure
- **Response parsers**: Unit test with hand-written valid/invalid responses
- **Schema validation**: Pydantic models enforce contracts between components

Mock at the LLM boundary for integration tests:

```python
class MockLLMClient:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
    
    def complete(self, prompt: str) -> str:
        # Return canned response based on prompt hash or pattern
```

### Property tests for aggregation

```python
@given(st.lists(valid_extraction_strategy()))
def test_aggregation_order_independent(extractions):
    shuffled = random.sample(extractions, len(extractions))
    result1 = aggregate_entity("x", extractions, registry)
    result2 = aggregate_entity("x", shuffled, registry)
    assert result1 == result2
```

## Session Context Hints

When session notes have ambiguous references, prepend natural language context:

```
[CONTEXT FOR THIS SESSION]
This session takes place on Mount Tambora, referred to throughout as 
"the mountain." The party is accompanied by Sera (the ranger from 
session 5).

[SESSION 7 NOTES BEGIN]
We set off at dawn...
```

Use natural language, not YAML or structured formats.

## Key Design Decisions

### Facts unify relationships

No separate relationship model. Facts have `object_entities` list. Relationships are queries: "facts where X is subject and Y is in object_entities."

### Contextual aliases are session-scoped

"The mountain" isn't stored as a global alias. Each extraction has a `context_resolutions` block documenting how contextual references were resolved for that session.

### Confidence is categorical, not numerical

LLMs don't produce calibrated probability scores. Natural language categories (`stated`, `rumor`, `player_theory`, etc.) are reliably distinguishable from text.

### Extraction snapshots are immutable

Re-extraction is a choice, not a requirement. Each extraction is valid relative to the registry version it used (recorded in `registry_commit`). Later registry improvements create *opportunity* for better extractions, not *invalidation* of existing ones.

### Registry edits are first-class

To merge entities or add aliases: edit `entity-registry.json`, commit with a message explaining the change, then optionally re-extract affected sessions.

## Dependencies

- Python 3.11+
- SCons
- Pydantic
- Anthropic Python SDK
- pytest (testing)
- Hypothesis (testing)

## Common Tasks

### Add a new session

1. Add `data/sessions/raw/session-NNN.txt`
2. Run `scons --session=NNN`

### Merge two entities

1. Edit `data/entity-registry.json`: combine aliases under one canonical name, delete the other
2. Commit the change
3. Run `scons aggregate` (re-aggregation will consolidate facts)
4. Optionally: `scons extract --all` to improve past extractions

### Fix an extraction error

1. Edit `data/sessions/extracted/session-NNN.json` directly, or
2. Delete it and re-run `scons --session=NNN` to re-extract

### Change the extraction prompt

1. Edit `pipeline/extraction/prompt.py`
2. Run `scons extract --all` to re-extract with new prompt

### Add a new entity type

Just use it. The `type` field isn't constrained to a fixed set.

### Add a new confidence category

1. Add to `ConfidenceLevel` enum in `wiki/models/fact.py`
2. Update extraction prompt to explain when to use it
3. Update rendering prompt to handle it appropriately
