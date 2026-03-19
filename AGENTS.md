# Wikify

A tool for extracting structured knowledge from notes and generating Wikipedia-style articles.

## Project Overview

A pipeline that:
1. **Extracts** facts from session notes using an LLM
2. **Splits** extractions into per-entity-per-session data files (mechanical)
3. **Registers** newly discovered entities into the registry (mechanical)
4. **Merges** entity-session files into per-entity data files (mechanical)
5. **Renders** entity data into wiki articles using an LLM

All files are version-controlled. The build is managed by SCons.

## Data Repository

The `data/` directory is a git submodule pointing to a separate repository ([aral](https://github.com/whittle/aral)). This separates tool development from data processing:

- **wikify repo**: Tool code, pipeline logic, tests
- **aral repo**: Session notes, extractions, entity registry, rendered articles

### Cloning

```bash
git clone --recursive git@github.com:whittle/wikify.git
# Or if already cloned:
git submodule update --init
```

### Design Doc

For a more in-depth look at the design of this knowledge pipeline, read `DESIGN.md`.

### Commit workflow

Data changes are committed in the submodule:

```bash
cd data
git add entity-registry.json
git commit -m "Add alias for Baron Aldric"
git push
```

The parent repo can optionally track submodule updates:

```bash
cd ..
git add data
git commit -m "Update data submodule"
```

## Repository Structure

```
wikify/
  wikify/
    models/           # Pydantic data models
      fact.py         # Fact, ConfidenceLevel
      entity.py       # Entity, SessionEntityFacts, EntityData
      extraction.py   # ExtractionResult, ContextResolution
      registry.py     # Registry, AliasIndex

    extraction/       # Session → structured facts
      prompt.py       # build_extraction_prompt(session, registry) -> str
      parser.py       # parse_extraction_response(raw) -> ExtractionResult
      extract.py      # extract_session(session, registry, client) -> ExtractionResult

    aggregation/      # Extractions → per-entity data
      split.py        # all_session_facts(extraction) -> list[SessionEntityFacts]
      merge.py        # merge_session_facts(entity_id, entity, session_facts) -> EntityData
      errors.py       # EntityNotFoundError, EntityMismatchError

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

  data/               # Git submodule (github.com/whittle/aral)
    sessions/
      raw/            # Input: session-001.txt, session-002.txt, ...
      prompts/        # Output: session-001.txt (full interpolated prompt)
      extracted/      # Output: session-001.json, session-002.json, ...
    entities/
      sessions/       # Intermediate: SessionEntityFacts (facts only, no metadata)
        session-001/  #   baron-aldric.json, thornwood.json, ...
        session-002/  #   ...
      data/           # Output: baron-aldric.json, ...
      articles/       # Output: baron-aldric.md, ...
    entity-registry.json

  SConstruct
  README.md
```

## Data Model

Models are defined in `wikify/models/`. Key types:

### Fact (`wikify/models/fact.py`)
- `subject_entity`: Primary entity this fact is about
- `object_entities`: Other entities referenced
- `text`: The fact content
- `category`: Classification (history, abilities, geography, etc.)
- `confidence`: ConfidenceLevel enum (stated, observed, character_claim, implied, rumor, player_theory, uncertain, superseded)

### ExtractionResult (`wikify/models/extraction.py`)
- `session_number`, `extracted_at`, `registry_commit`, `extractor_version`: Metadata
- `context_resolutions`: List of reference→entity mappings for this session
- `entities`: New entities discovered
- `facts`: Extracted facts

### Registry (`wikify/models/registry.py`)
- `entities`: dict mapping entity_id → Entity
- `get_entity(entity_id)`: Retrieve an Entity
- `merge_entity(entity_id, entity)`: Add or merge an entity (union aliases, min first_appearance)

### SessionEntityFacts (`wikify/models/entity.py`)
- Intermediate format: facts about an entity from a single session
- Contains only `entity_id`, `facts`, `referenced_by` (no entity metadata)
- Produced by split, consumed by merge

### EntityData (`wikify/models/entity.py`)
- Aggregated view of an entity for article rendering
- Entity metadata (`canonical_name`, `aliases`, `type`, `first_appearance`) from registry
- Facts and references from merged SessionEntityFacts files
- `sessions_appeared` derived from facts' `source_session`

## Build System

SCons manages the build. Key rules:

### Extraction requires clean registry

Before extraction runs, verify `entity-registry.json` matches HEAD:

```python
def get_data_repo_commit_sha("entity-registry.json") -> str:
    """Returns commit SHA of data repo if clean, raises if dirty or uncommitted."""
```

Each extraction records the registry commit in its output.

### Sequential extraction

Sessions must be extracted in order. Session N benefits from entities discovered in sessions 1 through N-1.

### Dependency flow

```
session-NNN.txt + registry → session-NNN.json (LLM extraction)
                           → sessions/prompts/session-NNN.txt (side effect: persisted prompt)
session-NNN.json → entities/sessions/session-NNN/*.json (mechanical split → SessionEntityFacts)
session-NNN.json → entity-registry.json (mechanical register, updates with discovered entities)
entities/sessions/*/entity-id.json + registry → entities/data/entity-id.json (mechanical merge → EntityData)
entities/data/entity-id.json → entities/articles/entity-id.md (LLM rendering)
```

The extraction step persists the full interpolated prompt (session text + known entities) to `sessions/prompts/` for debugging and reproducibility.

The register step merges newly discovered and changed entities from extractions
into the registry. This enables "Session N benefits from entities discovered in
sessions 1 through N-1" by automatically updating the registry with each
extraction's discoveries.

Split files contain only facts and references (SessionEntityFacts), not entity metadata.
The merge step combines facts from all sessions with entity metadata from the registry
to produce the final EntityData.

### Build commands

```bash
uv run python -m SCons extract --session=20        # Extract from session-20.txt
uv run python -m SCons aggregate                   # Rebuild aggregation only
uv run python -m SCons render                      # Rebuild dirty articles only
uv run python -m SCons render --article=thornwood  # Rebuild article even if not dirty
uv run python -m SCons --session=20                # Extract indicated session, aggregate, render as needed
```

## Testing Strategy

### What makes a test valuable

A test is valuable if it can fail when the code is wrong. Do not write tests that:

- **Test the framework**: Pydantic guarantees that models can be instantiated, fields return what was assigned, defaults match the schema, and serialization roundtrips. Don't test these.
- **Mirror the implementation**: `assert entity.name == "foo"` after setting `name="foo"` tests nothing—it cannot fail unless Python itself is broken.
- **Test type checking**: If the type checker verifies a property (e.g., `ConfidenceLevel` values are strings because it inherits from `str`), don't write a runtime test for it.

A test is valuable when it verifies:

- **Computed behavior**: Derived values like merged aliases—test that the derivation is correct.
- **Invariants across inputs**: Use property tests to verify that behavior holds for arbitrary valid inputs, not just one example.
- **Edge cases in logic**: Empty inputs, boundary conditions, error handling.
- **Integration contracts**: Parsing external formats, API responses, file formats with real-world quirks.

When writing model tests, ask: "What logic does this model contain beyond its schema?" If the answer is "none," the model likely needs no dedicated tests—the type checker and Pydantic's guarantees suffice.

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
@given(st.data())
def test_includes_all_subject_entities(data):
    """All subject entities from facts should get a SessionEntityFacts."""
    facts = data.draw(st.lists(st.builds(Fact), min_size=1))
    extraction = data.draw(
        st.builds(ExtractionResult, facts=st.just(facts), entities=st.just([]))
    )

    result = all_session_facts(extraction)

    subject_ids = {f.subject_entity for f in facts}
    result_ids = {sf.entity_id for sf in result}
    assert subject_ids <= result_ids
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

## Pre-commit Hooks

All commits must pass pre-commit hooks. Run `pre-commit run` before committing to check staged files. When updating the pre-commit hooks themselves (`.pre-commit-config.yaml`), run `pre-commit run --all` to verify all files pass.

Hooks configured in `.pre-commit-config.yaml`:

- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with a newline
- **check-yaml**: Validate YAML syntax
- **check-added-large-files**: Prevent large files from being committed
- **uv-lock**: Keep uv.lock in sync
- **uv-export**: Keep requirements exports in sync
- **ruff-check**: Lint Python code (with auto-fix)
- **ruff-format**: Format Python code
- **ty-check**: Type check with ty (`uv run ty check`)
- **pytest**: Run the test suite (`uv run python -m pytest`)

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

1. Edit `wikify/extraction/prompt.py`
2. Run `scons extract --all` to re-extract with new prompt

### Add a new entity type

Just use it. The `type` field isn't constrained to a fixed set.

### Add a new confidence category

1. Add to `ConfidenceLevel` enum in `wikify/models/fact.py`
2. Update extraction prompt to explain when to use it
3. Update rendering prompt to handle it appropriately
