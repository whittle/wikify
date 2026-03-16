"""Tests for the Registry model."""

from hypothesis import given, strategies as st

from wikify.models import Entity, Registry


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
    def test_merge_new_entity(self):
        """Merging a new entity adds it to the registry."""
        registry = Registry()
        entity = Entity(
            canonical_name="Baron Aldric",
            aliases=["The Baron"],
            type="person",
            first_appearance=1,
        )

        registry.merge_entity("baron-aldric", entity)

        assert "baron-aldric" in registry.entities
        assert registry.entities["baron-aldric"] == entity

    def test_merge_updates_canonical_name(self):
        """Merging updates canonical_name to the new value."""
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
            canonical_name="Lord Aldric",
            aliases=[],
            type="person",
            first_appearance=2,
        )

        registry.merge_entity("baron-aldric", new_entity)

        result = registry.entities["baron-aldric"]
        assert result.canonical_name == "Lord Aldric"
        # Old canonical name becomes an alias
        assert "Baron Aldric" in result.aliases

    def test_merge_unions_aliases(self):
        """Merging unions existing and new aliases."""
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["The Baron", "Aldric"],
                    type="person",
                    first_appearance=1,
                )
            }
        )
        new_entity = Entity(
            canonical_name="Baron Aldric",
            aliases=["Lord of the Realm", "Aldric"],
            type="person",
            first_appearance=2,
        )

        registry.merge_entity("baron-aldric", new_entity)

        result = registry.entities["baron-aldric"]
        assert set(result.aliases) == {"The Baron", "Aldric", "Lord of the Realm"}

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
