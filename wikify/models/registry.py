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

    def merge_entity(self, entity_id: str, entity: Entity) -> Entity:
        """Merge an entity into the registry.

        If entity_id doesn't exist, adds it. If it exists, merges:
        - canonical_name: uses new value
        - aliases: union of existing + new, excluding new canonical_name
        - type: uses new value
        - first_appearance: minimum of existing and new

        Returns the entity that was inserted or updated from the merge.
        """
        if entity_id not in self.entities:
            self.entities[entity_id] = entity
            return entity

        old_entity = self.entities[entity_id]
        new_entity = old_entity.merge(entity)
        self.entities[entity_id] = new_entity

        return new_entity
