"""Entity and EntityData models."""

from datetime import datetime

from pydantic import BaseModel

from .fact import ConfidenceLevel


class Entity(BaseModel):
    """An entity in the registry."""

    canonical_name: str
    aliases: list[str] = []
    type: str  # person, location, object, organization, phenomenon
    first_appearance: int  # Session number


class AggregatedFact(BaseModel):
    """A fact with source session information."""

    text: str
    category: str
    confidence: ConfidenceLevel
    object_entities: list[str] = []
    source_session: int


class Reference(BaseModel):
    """A reference to this entity from another entity's fact."""

    source_entity: str
    fact_text: str
    source_session: int


class EntityData(BaseModel):
    """Aggregated data for an entity, used to render wiki articles."""

    entity_id: str
    canonical_name: str
    aliases: list[str] = []
    type: str
    first_appearance: int

    facts: list[AggregatedFact] = []  # Facts where this entity is subject
    referenced_by: list[Reference] = []  # Facts from other entities mentioning this
    sessions_appeared: list[int] = []
    last_updated: datetime
