"""Tests for entity models."""

import copy

from hypothesis import given, strategies as st

from wikify.models.entity import Entity


def normalize_entity(entity: Entity) -> Entity:
    entity.aliases = list(set(entity.aliases) - {entity.canonical_name})
    return entity


class TestMergeEntity:
    @given(st.data())
    def test_merge_updates_canonical_name(self, data):
        """Merging updates canonical_name to the new value."""
        old_entity = data.draw(st.builds(Entity).map(normalize_entity))
        new_entity = data.draw(st.builds(Entity).map(normalize_entity))

        result = old_entity.merge(new_entity)

        assert result.canonical_name == new_entity.canonical_name

    @given(st.data())
    def test_merge_old_canonical_name_becomes_alias(self, data):
        """A merge that updates canonical_name adds the old value to aliases.."""
        old_entity = data.draw(st.builds(Entity).map(normalize_entity))
        new_canonical_name = data.draw(
            st.text().filter(lambda s: s != old_entity.canonical_name)
        )
        new_entity = copy.replace(old_entity, canonical_name=new_canonical_name)

        result = old_entity.merge(new_entity)

        assert old_entity.canonical_name in result.aliases

    @given(st.data())
    def test_merge_preserves_old_aliases(self, data):
        """Merging includes existing aliases, as long as none of them would become the new canonical name."""
        old_entity = data.draw(st.builds(Entity).map(normalize_entity))
        new_entity = data.draw(
            st.builds(Entity)
            .filter(lambda a: a.canonical_name not in old_entity.aliases)
            .map(normalize_entity)
        )

        result = old_entity.merge(new_entity)

        assert set(result.aliases) >= set(old_entity.aliases)

    @given(st.data())
    def test_merge_adds_new_aliases(self, data):
        """Merging includes new aliases."""
        old_entity = data.draw(st.builds(Entity).map(normalize_entity))
        new_aliases = data.draw(
            st.lists(st.text().filter(lambda s: s != old_entity.canonical_name))
        )
        new_entity = copy.replace(old_entity, aliases=new_aliases)

        result = old_entity.merge(new_entity)

        assert set(result.aliases) >= set(new_aliases)

    @given(st.data())
    def test_merge_excludes_new_canonical_from_aliases(self, data):
        """Merging excludes the new canonical_name from aliases."""
        old_entity = data.draw(
            st.builds(Entity)
            .map(normalize_entity)
            .filter(lambda a: len(a.aliases) >= 1)
        )
        new_canonical_name = data.draw(st.sampled_from(old_entity.aliases))
        new_entity = copy.replace(old_entity, canonical_name=new_canonical_name)

        result = old_entity.merge(new_entity)

        assert new_canonical_name not in result.aliases

    @given(st.data())
    def test_merge_uses_new_type(self, data):
        """Merging uses the new entity’s type."""
        old_entity = data.draw(st.builds(Entity).map(normalize_entity))
        new_entity = data.draw(st.builds(Entity).map(normalize_entity))

        result = old_entity.merge(new_entity)

        assert result.type == new_entity.type

    @given(st.data())
    def test_merge_uses_existing_first_appearance_where_lower(self, data):
        """Merging uses the existing first_appearance if that’s lower."""
        divider = data.draw(st.integers(min_value=0))
        old_entity = data.draw(
            st.builds(Entity, first_appearance=st.integers(max_value=divider)).map(
                normalize_entity
            )
        )
        new_entity = data.draw(
            st.builds(Entity, first_appearance=st.integers(min_value=divider)).map(
                normalize_entity
            )
        )

        result = old_entity.merge(new_entity)

        assert result.first_appearance == old_entity.first_appearance

    @given(st.data())
    def test_merge_uses_other_first_appearance_where_lower(self, data):
        """Merging uses the existing first_appearance if that’s lower."""
        divider = data.draw(st.integers(min_value=0))
        old_entity = data.draw(
            st.builds(Entity, first_appearance=st.integers(min_value=divider)).map(
                normalize_entity
            )
        )
        new_entity = data.draw(
            st.builds(Entity, first_appearance=st.integers(max_value=divider)).map(
                normalize_entity
            )
        )

        result = old_entity.merge(new_entity)

        assert result.first_appearance == new_entity.first_appearance

    @given(st.data())
    def test_merge_uses_existing_description_if_none_added(self, data):
        """Merging uses the existing description if other has no description."""
        old_entity = data.draw(st.builds(Entity, description=st.text()))
        new_entity = data.draw(st.builds(Entity, description=st.none()))

        result = old_entity.merge(new_entity)

        assert result.description == old_entity.description

    @given(st.data())
    def test_merge_uses_new_description_if_none_existing(self, data):
        """Merging uses the new description if self has no description."""
        old_entity = data.draw(st.builds(Entity, description=st.none()))
        new_entity = data.draw(st.builds(Entity, description=st.text()))

        result = old_entity.merge(new_entity)

        assert result.description == new_entity.description

    @given(st.data())
    def test_merge_concats_descriptions_if_both_present(self, data):
        """Merging concats the descriptions together, existing first, if neither is None."""
        old_entity = data.draw(st.builds(Entity, description=st.text()))
        new_entity = data.draw(st.builds(Entity, description=st.text()))

        result = old_entity.merge(new_entity)

        assert result.description == old_entity.description + new_entity.description
