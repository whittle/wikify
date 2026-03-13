"""Prompt builder for fact extraction."""

from wikify.models.registry import Registry


def build_extraction_prompt(session: str, registry: Registry) -> str:
    """Build LLM prompt for fact extraction from session notes.

    Args:
        session: Raw session text to extract facts from
        registry: Entity registry with known entities

    Returns:
        Complete prompt string for the LLM
    """
    known_entities_section = _build_known_entities_section(registry)

    return f"""\
You are a fact extractor for a tabletop RPG knowledge base. Your task is to \
extract structured facts from session notes.

{known_entities_section}

## Output Format

Return a JSON object with these fields:

```json
{{
  "context_resolutions": [
    {{"reference": "the mountain", "resolved_to": "mount-tambora"}}
  ],
  "entities": [
    {{
      "entity_id": "sera-ranger",
      "canonical_name": "Sera",
      "aliases": ["the ranger"],
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

**entities**: Only include NEW entities discovered in this session that are not in \
the known entities list above. Each entity needs:
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

## Session Notes

{session}

Return only the JSON object, no additional text."""


def _build_known_entities_section(registry: Registry) -> str:
    """Build the known entities section of the prompt."""
    if not registry.entities:
        return "## Known Entities\n\nNo entities are known yet."

    lines = ["## Known Entities\n"]
    for entity_id, entity in registry.entities.items():
        aliases_str = ""
        if entity.aliases:
            aliases_str = f" (aliases: {', '.join(entity.aliases)})"
        lines.append(
            f"- `{entity_id}`: **{entity.canonical_name}**{aliases_str} [{entity.type}]"
        )

    return "\n".join(lines)
