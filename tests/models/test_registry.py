"""Tests for the Registry model."""

from hypothesis import given, strategies as st

from wikify.models import Entity, Registry


def normalize_entity(entity: Entity) -> Entity:
    entity.aliases = list(set(entity.aliases) - {entity.canonical_name})
    return entity


class TestRegistry:
    def test_alias_index_for_empty_registry(self):
        """Empty registry has empty alias index."""
        registry = Registry()

        assert registry.alias_index == {}

    @given(st.builds(Registry))
    def test_alias_index_size(self, registry):
        """Alias index contains canonical names and aliases."""
        # Count expected entries (canonical name + aliases for each entity)
        expected_keys = set()
        for entity in registry.entities.values():
            expected_keys.add(entity.canonical_name.lower())
            for alias in entity.aliases:
                expected_keys.add(alias.lower())
        assert len(registry.alias_index) == len(expected_keys)

    @given(st.builds(Registry))
    def test_alias_index_is_lowercase(self, registry):
        """Alias index keys are lowercase for case-insensitive lookup."""
        for entity in registry.entities:
            assert entity.canonical_name.lower() in registry.alias_index
            for alias in entity.aliases:
                assert alias.lower() in registry.alias_index

    @given(
        st.dictionaries(st.text(min_size=1), st.builds(Entity), min_size=1)
        .filter(
            lambda entities: (
                # All names (canonical + aliases) must be unique across all entities
                len(
                    [
                        a
                        for e in entities.values()
                        for a in [e.canonical_name] + e.aliases
                    ]
                )
                == len(
                    {
                        a.lower()
                        for e in entities.values()
                        for a in [e.canonical_name] + e.aliases
                    }
                )
            )
        )
        .map(lambda entities: Registry(entities=entities))
    )
    def test_resolve_by_canonical_name(self, registry):
        """Registry resolves canonical names via lowercase normalization."""
        for entity_id, entity in registry.entities.items():
            assert registry.resolve(entity.canonical_name) == entity_id

    @given(
        st.dictionaries(st.text(min_size=1), st.builds(Entity), min_size=1)
        .filter(
            lambda entities: (
                len(
                    [
                        a
                        for e in entities.values()
                        for a in [e.canonical_name] + e.aliases
                    ]
                )
                == len(
                    {
                        a.lower()
                        for e in entities.values()
                        for a in [e.canonical_name] + e.aliases
                    }
                )
            )
        )
        .map(lambda entities: Registry(entities=entities))
    )
    def test_resolve_by_alias(self, registry):
        """Registry resolves aliases via lowercase normalization."""
        for entity_id, entity in registry.entities.items():
            for alias in entity.aliases:
                assert registry.resolve(alias) == entity_id

    @given(st.builds(Registry), st.text())
    def test_resolve_unknown_returns_none(self, registry, name):
        """Registry returns None for unknown names."""
        if name.lower() not in registry.alias_index:
            assert registry.resolve(name) is None

    @given(
        st.dictionaries(st.text(min_size=1), st.builds(Entity), min_size=1).map(
            lambda entities: Registry(entities=entities)
        ),
        st.data(),
    )
    def test_get_entity_success(self, registry, data):
        """Registry retrieves entities by ID where they are present."""
        (entity_id, entity) = data.draw(
            st.sampled_from(list(registry.entities.items()))
        )

        assert registry.get_entity(entity_id) == entity

    @given(st.builds(Registry), st.data())
    def test_get_entity_failure(self, registry, data):
        """Registry returns None when asked to retrieve an ID that isn’t present."""
        entity_id = data.draw(
            st.text().filter(lambda s: s not in registry.entities.keys())
        )

        assert registry.get_entity(entity_id) is None


class TestMergeEntity:
    @given(st.builds(Registry), st.data())
    def test_merge_new_entity_id(self, registry, data):
        """Merging a new entity adds it to the registry."""
        entity = data.draw(st.builds(Entity).map(normalize_entity))
        entity_id = data.draw(st.text().filter(lambda a: a not in registry.entities))

        result = registry.merge_entity(entity_id, entity)

        assert entity_id in registry.entities
        assert result == registry.entities[entity_id] == entity

    @given(st.dictionaries(st.text(), st.builds(Entity), min_size=1), st.data())
    def test_merge_existing_entity_id(self, entities, data):
        """Merging at a known entity_id updates the entity at that index."""
        registry = Registry(entities=entities)
        entity_id = data.draw(st.sampled_from(sorted(entities.keys())))
        old_entity = registry.entities[entity_id]
        new_entity = data.draw(st.builds(Entity))

        result = registry.merge_entity(entity_id, new_entity)

        assert result == old_entity.merge(new_entity)
