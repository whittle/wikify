"""Tests for SessionResolution model."""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from wikify.models import ExtractionResult, SessionResolution


class TestGeneratePassthrough:
    def test_session_number_matches(self):
        """Generated resolution should have same session_number as extraction."""
        extraction = ExtractionResult(
            session_number=42,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            registry_commit="abc123",
            extractor_version="1.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )

        result = SessionResolution.generate_passthrough(extraction)

        assert result.session_number == 42

    @given(st.builds(ExtractionResult))
    def test_all_entity_ids_have_resolutions(self, extraction):
        """Every collected entity_id should have a resolution entry."""
        result = SessionResolution.generate_passthrough(extraction)

        collected = extraction.collect_entity_ids()
        assert set(result.resolutions.keys()) == collected

    @given(st.builds(ExtractionResult))
    def test_all_resolutions_are_pass_through(self, extraction):
        """Generated resolutions should be identity mappings (id -> id)."""
        result = SessionResolution.generate_passthrough(extraction)

        for key, value in result.resolutions.items():
            assert key == value

    @given(st.builds(ExtractionResult))
    def test_resolutions_are_sorted(self, extraction):
        """Resolution keys should be sorted for consistent output."""
        result = SessionResolution.generate_passthrough(extraction)

        keys = list(result.resolutions.keys())
        assert keys == sorted(keys)
