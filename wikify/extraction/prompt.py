"""Prompt builder for fact extraction."""

from typing import Optional

from wikify.models.entity import Entity
from wikify.models.registry import Registry


def build_extraction_prompt(
    session: str, registry: Registry, context: Optional[str] = None
) -> str:
    """Build LLM prompt for fact extraction from session notes.

    Args:
        session: Raw session text to extract facts from
        registry: Entity registry with known entities
        context: Optional session context hints

    Returns:
        Complete prompt string for the LLM
    """
    known_entities_section = _build_known_entities_section(registry)
    context_section = _build_context_section(context)

    return f"""\
You are a fact extractor for a tabletop RPG knowledge base. Your task is to \
extract structured facts from session notes.

## Output Format

Return a JSON object with these fields:

```json
{{
  "context_resolutions": [
    {{"reference": "the mountain", "resolved_to": "mount-tambora"}}
  ],
  "entities": [
    {{
      "entity_id": "serafina-diallo",
      "canonical_name": "Serafina Diallo",
      "aliases": ["Sera", "Sera the ranger"],
      "type": "person"
    }}
  ],
  "facts": [
    {{
      "subject_entity": "baron-aldric",
      "object_entities": ["thornwood-keep"],
      "text": "Baron Aldric rules Thornwood Keep.",
      "category": "governance",
      "confidence": "stated"
    }}
  ]
}}
```

### Field Definitions

**context_resolutions**: Document how contextual references (like "the mountain" or \
"the old man") are resolved to entity_ids for this session.

**entities**: Only include new entities discovered in this session that are not \
in the known entities list above, or existing entities that need their \
canonical_name, aliases, or type updated. Each entity needs:
- `entity_id`: lowercase-hyphenated unique identifier
- `canonical_name`: the primary name for this entity
- `aliases`: other names/titles used for this entity
- `type`: one of person, location, object, organization, phenomenon, or similar

**facts**: Extracted facts. Each fact needs:
- `subject_entity`: entity_id of the primary entity this fact is about
- `object_entities`: list of entity_ids for other entities referenced in this fact
- `text`: the fact itself, written as a complete statement
- `category`: type of fact (history, abilities, geography, relationships, governance, \
events, etc.)
- `confidence`: one of:
  - `stated`: explicitly stated by narrator/GM
  - `observed`: directly witnessed by player characters
  - `character_claim`: stated by an NPC (may be unreliable)
  - `implied`: reasonably inferred from events
  - `rumor`: secondhand information, hearsay
  - `player_theory`: out-of-character player speculation
  - `uncertain`: ambiguous or possibly misunderstood
  - `superseded`: contradicted by later information

## Guidelines

1. Extract all meaningful facts, even small details
2. Use entity_ids from the known entities list when referencing entities in facts
3. Create new entities only for significant characters, places, or things
4. Be precise about confidence levels - don't upgrade rumors to stated facts
5. Include object_entities for any entities mentioned in the fact
6. Document context resolutions for pronouns or descriptive references
7. Do not include articles (a, the) at the start of entity names, aliases, or entity_ids
8. Context resolution references may include an article (a, the) at their start

## Known Entities

{known_entities_section}
{context_section}
## Session Notes

{session}

## Final Instructions

Return only the JSON object, no additional text.
"""


def _stringify_known_entity(entity_id: str, entity: Entity) -> str:
    """Markdown list item representation of an Entity."""
    aliases_str = ""
    if entity.aliases:
        aliases_str = f" (aliases: {', '.join(entity.aliases)})"
    description_str = ""
    if entity.description:
        description_str = f" {entity.description}"

    return f"- `{entity_id}` [{entity.type}]: **{entity.canonical_name}**{description_str}{aliases_str}"


def _build_known_entities_section(registry: Registry) -> str:
    """Build the known entities section of the prompt."""
    if not registry.entities:
        return "No entities are known yet."

    format_note = "ENTITY FORMAT:\n- `entity_id` [type]: **Canonical Name** optional description (aliases: optional)\n\n"

    lines = [
        _stringify_known_entity(entity_id, entity)
        for entity_id, entity in registry.entities.items()
    ]

    return format_note + "\n".join(lines)


def _build_context_section(context: Optional[str]) -> str:
    """Build the optional context section of the prompt."""
    if context is None:
        return ""

    return f"""
## Session Context

{context}

"""
