"""Tests for the Registry model."""

from hypothesis import given, strategies as st

from wikify.models import Entity, Registry


def normalize_entity(entity: Entity) -> Entity:
    entity.aliases = list(set(entity.aliases) - {entity.canonical_name})
    return entity


class TestRegistry:
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
