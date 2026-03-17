"""Entity and EntityData models."""

from typing import Optional

from pydantic import BaseModel

from .fact import ConfidenceLevel


class Entity(BaseModel):
    """An entity in the registry."""

    canonical_name: str
    aliases: list[str]
    type: str  # person, location, object, organization, phenomenon
    first_appearance: int  # Session number
    description: Optional[str]

    def merge(self, other: Entity) -> Entity:
        """Creates a new entity that is the result of merging other on top of self.

        Precondition: other represents a more recent extraction of the same
        entity. Both self and other have been normalized.

        Merge each field using the appropriate strategy:
        - canonical_name: uses other (more recent) value
        - aliases: union of existing + other, excluding new canonical_name
        - type: uses other (more recent) value
        - first_appearance: minimum of existing and other
        - description: string concatenation, existing first

        Postcondition: Does not alter self.

        """
        all_aliases = set(self.aliases) | set(other.aliases)

        # Old canonical name becomes an alias if different
        if self.canonical_name != other.canonical_name:
            all_aliases.add(self.canonical_name)
        all_aliases.discard(other.canonical_name)

        return Entity(
            canonical_name=other.canonical_name,
            aliases=sorted(all_aliases),
            type=other.type,
            first_appearance=min(self.first_appearance, other.first_appearance),
            description=self.concat_opt([self.description, other.description]),
        )

    def concat_opt(self, opts: list[Optional[str]]) -> Optional[str]:
        if all(a is None for a in opts):
            return None
        else:
            return "".join([a or "" for a in opts])


class AggregatedFact(BaseModel):
    """A fact with source session information."""

    text: str
    category: str
    confidence: ConfidenceLevel
    object_entities: list[str]
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
    aliases: list[str]
    type: str
    first_appearance: int

    facts: list[AggregatedFact]  # Facts where this entity is subject
    referenced_by: list[Reference]  # Facts from other entities mentioning this
    sessions_appeared: list[int]
