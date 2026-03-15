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

    def merge_entity(self, entity_id: str, entity: Entity) -> None:
        """Merge an entity into the registry.

        If entity_id doesn't exist, adds it. If it exists, merges:
        - canonical_name: uses new value
        - aliases: union of existing + new, excluding new canonical_name
        - type: uses new value
        - first_appearance: minimum of existing and new
        """
        if entity_id not in self.entities:
            self.entities[entity_id] = entity
            return

        existing = self.entities[entity_id]
        all_aliases = set(existing.aliases) | set(entity.aliases)
        # Old canonical name becomes an alias if different
        if existing.canonical_name != entity.canonical_name:
            all_aliases.add(existing.canonical_name)
        all_aliases.discard(entity.canonical_name)

        self.entities[entity_id] = Entity(
            canonical_name=entity.canonical_name,
            aliases=sorted(all_aliases),
            type=entity.type,
            first_appearance=min(existing.first_appearance, entity.first_appearance),
        )
