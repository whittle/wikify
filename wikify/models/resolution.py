"""Entity resolution models for mapping extracted entity_ids to registry entity_ids."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel

from .extraction import ExtractedEntity
from .fact import Fact

if TYPE_CHECKING:
    from .extraction import ExtractionResult


class SessionResolution(BaseModel):
    """Maps extracted entity_ids to resolved entity_ids for a session.

    Generated automatically as pass-through (id -> id), then manually edited
    to correct mismatches or merge duplicates.
    """

    session_number: int
    generated_at: datetime
    resolutions: dict[str, str | None]
    """Maps extracted entity_id to resolved entity_id.

    - Same value: pass-through (no change needed)
    - Different value: correction/merge to existing entity
    - None: exclude this entity from processing
    """

    def resolve(self, entity_id: str) -> str | None:
        """Resolve an entity_id through the mapping.

        Returns the resolved entity_id, or None if excluded.
        Raises KeyError if entity_id is not in the resolution map.
        """
        return self.resolutions[entity_id]

    def all_extracted_ids(self) -> set[str]:
        """Return all entity_ids from the extraction (keys)."""
        return set(self.resolutions.keys())

    def all_resolved_ids(self) -> set[str]:
        """Return all resolved entity_ids (non-None values)."""
        return {v for v in self.resolutions.values() if v is not None}

    @classmethod
    def generate_passthrough(cls, extraction: ExtractionResult) -> SessionResolution:
        """Generate a pass-through resolution for an extraction.

        Creates identity mappings (id -> id) for all entity_ids in the extraction.
        This file can then be manually edited to correct mismatches.
        """
        entity_ids = extraction.collect_entity_ids()

        return cls(
            session_number=extraction.session_number,
            generated_at=datetime.now(timezone.utc),
            resolutions={eid: eid for eid in sorted(entity_ids)},
        )


class ResolvedExtraction(BaseModel):
    """ExtractionResult with SessionResolution applied.

    Input to split/register steps. Contains only fields used in aggregation.
    Excludes extraction-only metadata (extracted_at, registry_commit,
    extractor_version, context_resolutions).
    """

    session_number: int
    entities: list[ExtractedEntity]
    facts: list[Fact]

    # TODO: break this out into smaller pieces
    @classmethod
    def from_extraction_and_resolution(
        cls,
        extraction: ExtractionResult,
        resolution: SessionResolution,
    ) -> ResolvedExtraction:
        """Apply resolution to translate all entity_ids.

        - Translates entity_id in entities, subject_entity and object_entities in facts
        - Excludes entities/facts where resolution returns None
        - Merges entities that resolve to the same target ID
        - Raises KeyError if entity_id not in resolution map
        """
        # Resolve entities, grouping by resolved ID for merging
        resolved_entities: dict[str, ExtractedEntity] = {}
        for entity in extraction.entities:
            resolved_id = resolution.resolve(entity.entity_id)
            if resolved_id is None:
                continue

            if resolved_id in resolved_entities:
                # Merge: combine aliases, take min first_appearance
                existing = resolved_entities[resolved_id]
                merged_aliases = set(existing.aliases)
                merged_aliases.update(entity.aliases)
                # Add old canonical name as alias if different
                if entity.canonical_name != existing.canonical_name:
                    merged_aliases.add(entity.canonical_name)

                resolved_entities[resolved_id] = ExtractedEntity(
                    entity_id=resolved_id,
                    canonical_name=existing.canonical_name,
                    aliases=sorted(merged_aliases),
                    type=existing.type,
                    first_appearance=min(
                        existing.first_appearance, entity.first_appearance
                    ),
                )
            else:
                resolved_entities[resolved_id] = ExtractedEntity(
                    entity_id=resolved_id,
                    canonical_name=entity.canonical_name,
                    aliases=entity.aliases,
                    type=entity.type,
                    first_appearance=entity.first_appearance,
                )

        # Resolve facts, translating subject_entity and object_entities
        resolved_facts: list[Fact] = []
        for fact in extraction.facts:
            resolved_subject = resolution.resolve(fact.subject_entity)
            if resolved_subject is None:
                continue

            resolved_objects: list[str] = []
            for obj_id in fact.object_entities:
                resolved_obj = resolution.resolve(obj_id)
                if resolved_obj is not None:
                    resolved_objects.append(resolved_obj)

            resolved_facts.append(
                Fact(
                    subject_entity=resolved_subject,
                    object_entities=resolved_objects,
                    text=fact.text,
                    category=fact.category,
                    confidence=fact.confidence,
                )
            )

        return cls(
            session_number=extraction.session_number,
            entities=list(resolved_entities.values()),
            facts=resolved_facts,
        )
