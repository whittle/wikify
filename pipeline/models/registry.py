"""Registry model for managing entities and aliases."""

from pydantic import BaseModel, computed_field

from .entity import Entity


class Registry(BaseModel):
    """Registry of all known entities and their aliases."""

    entities: dict[str, Entity] = {}  # entity_id -> Entity

    @computed_field
    @property
    def alias_index(self) -> dict[str, str]:
        """Build alias index from entities. Maps lowercase alias -> entity_id."""
        index: dict[str, str] = {}
        for entity_id, entity in self.entities.items():
            # Index the canonical name
            index[entity.canonical_name.lower()] = entity_id
            # Index all aliases
            for alias in entity.aliases:
                index[alias.lower()] = entity_id
        return index

    def resolve(self, name: str) -> str | None:
        """Resolve a name to an entity_id, or None if not found."""
        return self.alias_index.get(name.lower())

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)
