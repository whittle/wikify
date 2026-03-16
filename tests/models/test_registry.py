"""Tests for the Registry model."""

import copy

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
    def test_merge_new_entity(self, registry, data):
        """Merging a new entity adds it to the registry."""
        entity = data.draw(st.builds(Entity).map(normalize_entity))
        entity_id = data.draw(st.text().filter(lambda a: a not in registry.entities))

        result = registry.merge_entity(entity_id, entity)

        assert entity_id in registry.entities
        assert result == registry.entities[entity_id] == entity

    @given(st.dictionaries(st.text(), st.builds(Entity), min_size=1), st.data())
    def test_merge_updates_canonical_name(self, entities, data):
        """Merging updates canonical_name to the new value."""
        registry = Registry(entities=entities)
        entity_id = data.draw(st.sampled_from(sorted(entities.keys())))
        new_canonical_name = data.draw(st.text())
        entity = copy.replace(entities[entity_id], canonical_name=new_canonical_name)

        result = registry.merge_entity(entity_id, entity)

        assert result.canonical_name == new_canonical_name

    @given(st.data())
    def test_merge_old_canonical_name_becomes_alias(self, data):
        """A merge that updates canonical_name adds the old value to aliases.."""
        entities = data.draw(
            st.dictionaries(
                st.text(), st.builds(Entity).map(normalize_entity), min_size=1
            )
        )
        registry = Registry(entities=entities)
        entity_id = data.draw(st.sampled_from(sorted(entities.keys())))
        old_canonical_name = entities[entity_id].canonical_name
        new_canonical_name = data.draw(
            st.text().filter(lambda s: s != old_canonical_name)
        )
        entity = copy.replace(entities[entity_id], canonical_name=new_canonical_name)

        result = registry.merge_entity(entity_id, entity)

        assert old_canonical_name in result.aliases

    @given(st.data())
    def test_merge_preserves_old_aliases(self, data):
        """Merging includes existing aliases."""
        entities = data.draw(
            st.dictionaries(
                st.text(), st.builds(Entity).map(normalize_entity), min_size=1
            )
        )
        registry = Registry(entities=entities)
        entity_id = data.draw(st.sampled_from(sorted(entities.keys())))
        old_entity = entities[entity_id]
        new_aliases = data.draw(
            st.lists(st.text().filter(lambda s: s != old_entity.canonical_name))
        )
        new_entity = copy.replace(entities[entity_id], aliases=new_aliases)

        result = registry.merge_entity(entity_id, new_entity)

        assert set(result.aliases) >= set(old_entity.aliases)

    @given(st.data())
    def test_merge_adds_new_aliases(self, data):
        """Merging includes new aliases."""
        entities = data.draw(
            st.dictionaries(
                st.text(), st.builds(Entity).map(normalize_entity), min_size=1
            )
        )
        registry = Registry(entities=entities)
        entity_id = data.draw(st.sampled_from(sorted(entities.keys())))
        old_entity = entities[entity_id]
        new_aliases = data.draw(
            st.lists(st.text().filter(lambda s: s != old_entity.canonical_name))
        )
        new_entity = copy.replace(entities[entity_id], aliases=new_aliases)

        result = registry.merge_entity(entity_id, new_entity)

        assert set(result.aliases) >= set(new_aliases)

    def test_merge_excludes_new_canonical_from_aliases(self):
        """Merging excludes the new canonical_name from aliases."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Aldric",
                    aliases=["Baron Aldric"],
                    type="person",
                    first_appearance=1,
                )
            }
        )
        new_entity = Entity(
            canonical_name="Baron Aldric",
            aliases=[],
            type="person",
            first_appearance=2,
        )

        registry.merge_entity("baron-aldric", new_entity)

        result = registry.entities["baron-aldric"]
        assert result.canonical_name == "Baron Aldric"
        assert "Baron Aldric" not in result.aliases
        assert "Aldric" in result.aliases

    def test_merge_uses_minimum_first_appearance(self):
        """Merging uses the minimum first_appearance."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=[],
                    type="person",
                    first_appearance=5,
                )
            }
        )
        new_entity = Entity(
            canonical_name="Baron Aldric",
            aliases=[],
            type="person",
            first_appearance=3,
        )

        registry.merge_entity("baron-aldric", new_entity)

        assert registry.entities["baron-aldric"].first_appearance == 3

    def test_merge_uses_new_type(self):
        """Merging uses the new entity’s type."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=[],
                    type="person",
                    first_appearance=1,
                )
            }
        )
        new_entity = Entity(
            canonical_name="Baron Aldric",
            aliases=[],
            type="noble",
            first_appearance=2,
        )

        registry.merge_entity("baron-aldric", new_entity)

        assert registry.entities["baron-aldric"].type == "noble"

    def test_merge_sorts_aliases(self):
        """Merged aliases are sorted."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["Zebra", "Alpha"],
                    type="person",
                    first_appearance=1,
                )
            }
        )
        new_entity = Entity(
            canonical_name="Baron Aldric",
            aliases=["Middle", "Beta"],
            type="person",
            first_appearance=2,
        )

        registry.merge_entity("baron-aldric", new_entity)

        result = registry.entities["baron-aldric"]
        assert result.aliases == sorted(result.aliases)
