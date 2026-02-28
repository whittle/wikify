"""Tests for extraction prompt builder."""

from hypothesis import given, settings
from hypothesis import strategies as st

from wikify.extraction.prompt import build_extraction_prompt
from wikify.models.entity import Entity
from wikify.models.registry import Registry


class TestBuildExtractionPrompt:
    """Tests for build_extraction_prompt."""

    def test_returns_nonempty_string(self) -> None:
        """Prompt builder returns a non-empty string."""
        session = "The party entered the dungeon."
        registry = Registry()

        result = build_extraction_prompt(session, registry)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_session_text(self) -> None:
        """Session text appears somewhere in the prompt."""
        session = "Baron Aldric greeted the party at Thornwood Keep."
        registry = Registry()

        result = build_extraction_prompt(session, registry)

        assert session in result

    def test_known_entities_appear_in_prompt(self) -> None:
        """Entity names from registry appear in the prompt."""
        session = "The party traveled north."
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["the Baron", "Lord Aldric"],
                    type="person",
                    first_appearance=1,
                ),
                "thornwood-keep": Entity(
                    canonical_name="Thornwood Keep",
                    aliases=["the Keep"],
                    type="location",
                    first_appearance=1,
                ),
            }
        )

        result = build_extraction_prompt(session, registry)

        assert "Baron Aldric" in result
        assert "Thornwood Keep" in result

    def test_aliases_appear_in_prompt(self) -> None:
        """Entity aliases appear in the prompt."""
        session = "The party traveled north."
        registry = Registry(
            entities={
                "baron-aldric": Entity(
                    canonical_name="Baron Aldric",
                    aliases=["the Baron", "Lord Aldric"],
                    type="person",
                    first_appearance=1,
                ),
            }
        )

        result = build_extraction_prompt(session, registry)

        assert "the Baron" in result
        assert "Lord Aldric" in result

    def test_empty_registry_produces_valid_prompt(self) -> None:
        """Empty registry still produces a usable prompt."""
        session = "The adventure begins."
        registry = Registry()

        result = build_extraction_prompt(session, registry)

        assert session in result
        assert isinstance(result, str)


# Property-based tests

entity_strategy = st.builds(
    Entity,
    canonical_name=st.text(min_size=1, max_size=50),
    aliases=st.lists(st.text(min_size=1, max_size=30), max_size=5),
    type=st.sampled_from(["person", "location", "object", "organization"]),
    first_appearance=st.integers(min_value=1, max_value=100),
)

registry_strategy = st.builds(
    Registry,
    entities=st.dictionaries(
        keys=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-"),
            min_size=1,
            max_size=30,
        ),
        values=entity_strategy,
        max_size=10,
    ),
)


class TestPropertyBasedPrompt:
    """Property-based tests for prompt builder."""

    @given(session=st.text(min_size=1, max_size=1000), registry=registry_strategy)
    @settings(max_examples=30)
    def test_session_always_appears_in_prompt(
        self, session: str, registry: Registry
    ) -> None:
        """Session text always appears in the generated prompt."""
        result = build_extraction_prompt(session, registry)
        assert session in result

    @given(registry=registry_strategy)
    @settings(max_examples=30)
    def test_all_canonical_names_appear(self, registry: Registry) -> None:
        """All canonical entity names from registry appear in prompt."""
        session = "Test session."
        result = build_extraction_prompt(session, registry)

        for entity in registry.entities.values():
            assert entity.canonical_name in result
