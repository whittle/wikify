"""Extraction result models."""

from datetime import datetime

from pydantic import BaseModel

from .fact import Fact


class ContextResolution(BaseModel):
    """Maps a contextual reference to an entity_id."""

    reference: str  # e.g., "the mountain"
    resolved_to: str  # entity_id, e.g., "mount-tambora"


class ExtractedEntity(BaseModel):
    """An entity discovered during extraction."""

    entity_id: str
    canonical_name: str
    aliases: list[str] = []
    type: str
    first_appearance: int


class ExtractionResult(BaseModel):
    """Result of extracting facts from a session."""

    session_number: int
    extracted_at: datetime
    registry_commit: str  # Git SHA of registry used
    extractor_version: str

    context_resolutions: list[ContextResolution]
    entities: list[ExtractedEntity]
    facts: list[Fact]

    def collect_entity_ids(self) -> set[str]:
        """Collect all entity_ids referenced in this extraction.

        Includes:
        - entities[*].entity_id (discovered entities)
        - facts[*].subject_entity
        - facts[*].object_entities
        - context_resolutions[*].resolved_to
        """
        ids: set[str] = set()

        for entity in self.entities:
            ids.add(entity.entity_id)

        for fact in self.facts:
            ids.add(fact.subject_entity)
            ids.update(fact.object_entities)

        for resolution in self.context_resolutions:
            ids.add(resolution.resolved_to)

        return ids
