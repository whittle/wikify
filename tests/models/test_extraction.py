"""Tests for extraction models."""

from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wikify.models import (
    ConfidenceLevel,
    ContextResolution,
    ExtractedEntity,
    ExtractionResult,
    Fact,
    ResolvedExtraction,
    SessionResolution,
)


class TestCollectEntityIds:
    def test_empty_extraction(self):
        """An extraction with no data should produce no entity_ids."""
        extraction = ExtractionResult(
            session_number=1,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            registry_commit="abc123",
            extractor_version="1.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )

        result = extraction.collect_entity_ids()

        assert result == set()

    @given(st.data())
    def test_includes_entity_ids_from_entities(self, data):
        """Entity IDs from the entities list should be collected."""
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda e: e.entity_id
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.just(entities),
                facts=st.just([]),
                context_resolutions=st.just([]),
            )
        )

        result = extraction.collect_entity_ids()

        entity_ids = {e.entity_id for e in entities}
        assert entity_ids <= result

    @given(st.data())
    def test_includes_subject_entities_from_facts(self, data):
        """Subject entities from facts should be collected."""
        facts = data.draw(st.lists(st.builds(Fact), min_size=1))
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.just([]),
                facts=st.just(facts),
                context_resolutions=st.just([]),
            )
        )

        result = extraction.collect_entity_ids()

        subject_ids = {f.subject_entity for f in facts}
        assert subject_ids <= result

    @given(st.data())
    def test_includes_object_entities_from_facts(self, data):
        """Object entities from facts should be collected."""
        facts = data.draw(
            st.lists(
                st.builds(Fact, object_entities=st.lists(st.text(), min_size=1)),
                min_size=1,
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.just([]),
                facts=st.just(facts),
                context_resolutions=st.just([]),
            )
        )

        result = extraction.collect_entity_ids()

        object_ids = {eid for f in facts for eid in f.object_entities}
        assert object_ids <= result

    @given(st.data())
    def test_includes_resolved_to_from_context_resolutions(self, data):
        """Resolved entity IDs from context_resolutions should be collected."""
        context_resolutions = data.draw(
            st.lists(st.builds(ContextResolution), min_size=1)
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.just([]),
                facts=st.just([]),
                context_resolutions=st.just(context_resolutions),
            )
        )

        result = extraction.collect_entity_ids()

        resolved_ids = {cr.resolved_to for cr in context_resolutions}
        assert resolved_ids <= result


class TestResolvedExtraction:
    """Tests for ResolvedExtraction.from_extraction_and_resolution."""

    def _make_extraction(
        self,
        entities: list[ExtractedEntity] | None = None,
        facts: list[Fact] | None = None,
    ) -> ExtractionResult:
        return ExtractionResult(
            session_number=1,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            registry_commit="abc123",
            extractor_version="1.0",
            context_resolutions=[],
            entities=entities or [],
            facts=facts or [],
        )

    def _make_resolution(self, resolutions: dict[str, str | None]) -> SessionResolution:
        return SessionResolution(
            session_number=1,
            generated_at=datetime.now(timezone.utc),
            resolutions=resolutions,
        )

    def test_passthrough_translates_entity_ids(self):
        """Pass-through resolution preserves entity_ids unchanged."""
        entity = ExtractedEntity(
            entity_id="baron-aldric",
            canonical_name="Baron Aldric",
            aliases=[],
            type="npc",
            first_appearance=1,
        )
        fact = Fact(
            subject_entity="baron-aldric",
            object_entities=["thornwood"],
            text="The Baron rules Thornwood.",
            category="politics",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(entities=[entity], facts=[fact])
        resolution = self._make_resolution(
            {
                "baron-aldric": "baron-aldric",
                "thornwood": "thornwood",
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert len(result.entities) == 1
        assert result.entities[0].entity_id == "baron-aldric"
        assert len(result.facts) == 1
        assert result.facts[0].subject_entity == "baron-aldric"
        assert result.facts[0].object_entities == ["thornwood"]

    def test_translates_entity_ids(self):
        """Resolution remaps entity_ids to new values."""
        entity = ExtractedEntity(
            entity_id="baron-aldric",
            canonical_name="Baron Aldric",
            aliases=[],
            type="npc",
            first_appearance=1,
        )
        fact = Fact(
            subject_entity="baron-aldric",
            object_entities=["thorn-wood"],
            text="The Baron rules Thornwood.",
            category="politics",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(entities=[entity], facts=[fact])
        resolution = self._make_resolution(
            {
                "baron-aldric": "aldric",
                "thorn-wood": "thornwood",
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert result.entities[0].entity_id == "aldric"
        assert result.facts[0].subject_entity == "aldric"
        assert result.facts[0].object_entities == ["thornwood"]

    def test_excludes_entities_with_none_resolution(self):
        """Entities resolving to None are excluded."""
        entity1 = ExtractedEntity(
            entity_id="keep-me",
            canonical_name="Keep Me",
            aliases=[],
            type="npc",
            first_appearance=1,
        )
        entity2 = ExtractedEntity(
            entity_id="exclude-me",
            canonical_name="Exclude Me",
            aliases=[],
            type="npc",
            first_appearance=1,
        )
        extraction = self._make_extraction(entities=[entity1, entity2])
        resolution = self._make_resolution(
            {
                "keep-me": "keep-me",
                "exclude-me": None,
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert len(result.entities) == 1
        assert result.entities[0].entity_id == "keep-me"

    def test_excludes_facts_with_none_subject_resolution(self):
        """Facts with subject_entity resolving to None are excluded."""
        fact1 = Fact(
            subject_entity="keep-me",
            object_entities=[],
            text="Keep this fact.",
            category="test",
            confidence=ConfidenceLevel.STATED,
        )
        fact2 = Fact(
            subject_entity="exclude-me",
            object_entities=[],
            text="Exclude this fact.",
            category="test",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(facts=[fact1, fact2])
        resolution = self._make_resolution(
            {
                "keep-me": "keep-me",
                "exclude-me": None,
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert len(result.facts) == 1
        assert result.facts[0].subject_entity == "keep-me"

    def test_excludes_object_entities_with_none_resolution(self):
        """Object entities resolving to None are removed from the list."""
        fact = Fact(
            subject_entity="subject",
            object_entities=["keep-obj", "exclude-obj"],
            text="A fact with mixed objects.",
            category="test",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(facts=[fact])
        resolution = self._make_resolution(
            {
                "subject": "subject",
                "keep-obj": "keep-obj",
                "exclude-obj": None,
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert result.facts[0].object_entities == ["keep-obj"]

    def test_merges_entities_resolving_to_same_id(self):
        """Entities resolving to the same ID are merged."""
        entity1 = ExtractedEntity(
            entity_id="baron-aldric",
            canonical_name="Baron Aldric",
            aliases=["The Baron"],
            type="npc",
            first_appearance=2,
        )
        entity2 = ExtractedEntity(
            entity_id="lord-aldric",
            canonical_name="Lord Aldric",
            aliases=["Lord A"],
            type="npc",
            first_appearance=1,
        )
        extraction = self._make_extraction(entities=[entity1, entity2])
        resolution = self._make_resolution(
            {
                "baron-aldric": "aldric",
                "lord-aldric": "aldric",
            }
        )

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert len(result.entities) == 1
        merged = result.entities[0]
        assert merged.entity_id == "aldric"
        # First canonical name is preserved
        assert merged.canonical_name == "Baron Aldric"
        # Second canonical name becomes an alias
        assert "Lord Aldric" in merged.aliases
        # All aliases are merged
        assert "The Baron" in merged.aliases
        assert "Lord A" in merged.aliases
        # Minimum first_appearance is used
        assert merged.first_appearance == 1

    def test_raises_keyerror_for_unknown_entity_id(self):
        """KeyError is raised if entity_id not in resolution map."""
        entity = ExtractedEntity(
            entity_id="unknown",
            canonical_name="Unknown",
            aliases=[],
            type="npc",
            first_appearance=1,
        )
        extraction = self._make_extraction(entities=[entity])
        resolution = self._make_resolution({})  # Empty resolution

        with pytest.raises(KeyError):
            ResolvedExtraction.from_extraction_and_resolution(extraction, resolution)

    def test_raises_keyerror_for_unknown_subject_entity(self):
        """KeyError is raised if fact subject_entity not in resolution map."""
        fact = Fact(
            subject_entity="unknown",
            object_entities=[],
            text="Unknown subject.",
            category="test",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(facts=[fact])
        resolution = self._make_resolution({})

        with pytest.raises(KeyError):
            ResolvedExtraction.from_extraction_and_resolution(extraction, resolution)

    def test_raises_keyerror_for_unknown_object_entity(self):
        """KeyError is raised if fact object_entity not in resolution map."""
        fact = Fact(
            subject_entity="subject",
            object_entities=["unknown"],
            text="Unknown object.",
            category="test",
            confidence=ConfidenceLevel.STATED,
        )
        extraction = self._make_extraction(facts=[fact])
        resolution = self._make_resolution({"subject": "subject"})

        with pytest.raises(KeyError):
            ResolvedExtraction.from_extraction_and_resolution(extraction, resolution)

    def test_preserves_session_number(self):
        """Session number is preserved from extraction."""
        extraction = ExtractionResult(
            session_number=42,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            registry_commit="abc123",
            extractor_version="1.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )
        resolution = self._make_resolution({})

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert result.session_number == 42

    def test_excludes_extraction_metadata(self):
        """Resolved extraction does not have extraction metadata fields."""
        extraction = self._make_extraction()
        resolution = self._make_resolution({})

        result = ResolvedExtraction.from_extraction_and_resolution(
            extraction, resolution
        )

        assert not hasattr(result, "extracted_at")
        assert not hasattr(result, "registry_commit")
        assert not hasattr(result, "extractor_version")
        assert not hasattr(result, "context_resolutions")
