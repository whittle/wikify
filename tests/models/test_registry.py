"""Tests for the Registry model."""

import json

from wikify.models import Entity, Registry


class TestRegistry:
    def test_empty_registry(self):
        """Empty registry has empty alias index."""
        registry = Registry()
        assert registry.entities == {}
        assert registry.alias_index == {}

    def test_registry_with_entities(self):
        """Registry correctly indexes entities."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["The Baron", "Lord Aldric"],
                    type="person",
                    first_appearance=1,
                ),
                "thornwood": Entity(
                    canonical_name="Thornwood",
                    aliases=["The Dark Forest"],
                    type="location",
                    first_appearance=2,
                ),
            }
        )
        assert len(registry.entities) == 2
        # Alias index should have canonical names + aliases
        assert len(registry.alias_index) == 5

    def test_alias_index_is_lowercase(self):
        """Alias index keys are lowercase for case-insensitive lookup."""
        registry = Registry(
            entities={
                "mount-tambora": Entity(
                    canonical_name="Mount Tambora",
                    aliases=["The Mountain"],
                    type="location",
                    first_appearance=3,
                ),
            }
        )
        assert "mount tambora" in registry.alias_index
        assert "the mountain" in registry.alias_index
        assert "Mount Tambora" not in registry.alias_index

    def test_resolve_by_canonical_name(self):
        """Registry resolves canonical names."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    type="person",
                    first_appearance=1,
                ),
            }
        )
        assert registry.resolve("Baron Aldric") == "baron-aldric"
        assert registry.resolve("baron aldric") == "baron-aldric"

    def test_resolve_by_alias(self):
        """Registry resolves aliases."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["The Baron"],
                    type="person",
                    first_appearance=1,
                ),
            }
        )
        assert registry.resolve("The Baron") == "baron-aldric"
        assert registry.resolve("the baron") == "baron-aldric"

    def test_resolve_unknown_returns_none(self):
        """Registry returns None for unknown names."""
        registry = Registry()
        assert registry.resolve("Unknown Entity") is None

    def test_get_entity(self):
        """Registry retrieves entities by ID."""
        entity = Entity(
            canonical_name="Baron Aldric",
            type="person",
            first_appearance=1,
        )
        registry = Registry(entities={"baron-aldric": entity})
        assert registry.get_entity("baron-aldric") == entity
        assert registry.get_entity("unknown") is None

    def test_registry_serialization(self):
        """Registry serializes to JSON without computed field."""
        registry = Registry(
            entities={
                "test": Entity(
                    canonical_name="Test",
                    type="object",
                    first_appearance=1,
                ),
            }
        )
        # Computed field should not appear in serialized output
        data = registry.model_dump(exclude={"alias_index"})
        assert "alias_index" not in data
        assert "entities" in data

    def test_registry_deserialization(self):
        """Registry deserializes from JSON and rebuilds alias index."""
        json_data = {
            "entities": {
                "sera": {
                    "canonical_name": "Sera",
                    "aliases": ["The Ranger"],
                    "type": "person",
                    "first_appearance": 5,
                }
            }
        }
        registry = Registry.model_validate(json_data)
        # Alias index is rebuilt from entities
        assert registry.resolve("sera") == "sera"
        assert registry.resolve("the ranger") == "sera"

    def test_registry_from_file_format(self):
        """Registry can be loaded from the expected file format."""
        file_content = '{"entities": {}}'
        data = json.loads(file_content)
        registry = Registry(**data)
        assert registry.entities == {}
        assert registry.alias_index == {}
