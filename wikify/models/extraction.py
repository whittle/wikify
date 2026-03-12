"""Extraction result models."""

from datetime import datetime

from pydantic import BaseModel

from .fact import Fact


class ContextResolution(BaseModel):
    """Maps a contextual reference to a canonical entity."""

    reference: str  # e.g., "the mountain"
    resolved_to: str  # e.g., "Mount Tambora"


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
