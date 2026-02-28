"""Tests for extraction response parser."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wikify.extraction.errors import InvalidJSONError, SchemaValidationError
from wikify.extraction.parser import ParsedExtraction, parse_extraction_response
from wikify.models.fact import ConfidenceLevel


class TestParseExtractionResponse:
    """Unit tests for parse_extraction_response."""

    def test_parses_valid_minimal_response(self) -> None:
        """Empty arrays parse correctly."""
        raw = json.dumps({"context_resolutions": [], "entities": [], "facts": []})
        result = parse_extraction_response(raw)

        assert result.context_resolutions == []
        assert result.entities == []
        assert result.facts == []

    def test_parses_valid_full_response(self) -> None:
        """A complete response with all fields parses correctly."""
        raw = json.dumps(
            {
                "context_resolutions": [
                    {"reference": "the mountain", "resolved_to": "Mount Tambora"}
                ],
                "entities": [
                    {
                        "entity_id": "sera-ranger",
                        "canonical_name": "Sera",
                        "aliases": ["the ranger"],
                        "type": "person",
                    }
                ],
                "facts": [
                    {
                        "subject_entity": "Baron Aldric",
                        "object_entities": ["Thornwood Keep"],
                        "text": "Baron Aldric rules Thornwood Keep.",
                        "category": "governance",
                        "confidence": "stated",
                    }
                ],
            }
        )
        result = parse_extraction_response(raw)

        assert len(result.context_resolutions) == 1
        assert result.context_resolutions[0].reference == "the mountain"
        assert result.context_resolutions[0].resolved_to == "Mount Tambora"

        assert len(result.entities) == 1
        assert result.entities[0].entity_id == "sera-ranger"
        assert result.entities[0].canonical_name == "Sera"
        assert result.entities[0].aliases == ["the ranger"]
        assert result.entities[0].type == "person"

        assert len(result.facts) == 1
        assert result.facts[0].subject_entity == "Baron Aldric"
        assert result.facts[0].confidence == ConfidenceLevel.STATED

    def test_raises_invalid_json_error_for_malformed_json(self) -> None:
        """Non-JSON input raises InvalidJSONError."""
        raw = "this is not json"

        with pytest.raises(InvalidJSONError) as exc_info:
            parse_extraction_response(raw)

        assert exc_info.value.raw == raw
        assert "Invalid JSON" in str(exc_info.value)

    def test_raises_invalid_json_error_for_truncated_json(self) -> None:
        """Truncated JSON raises InvalidJSONError."""
        raw = '{"facts": ['

        with pytest.raises(InvalidJSONError) as exc_info:
            parse_extraction_response(raw)

        assert exc_info.value.raw == raw

    def test_raises_schema_error_for_missing_required_field(self) -> None:
        """Missing required field in fact raises SchemaValidationError."""
        raw = json.dumps(
            {
                "facts": [
                    {
                        "subject_entity": "Baron Aldric",
                        # missing text, category, confidence
                    }
                ]
            }
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            parse_extraction_response(raw)

        assert exc_info.value.raw == raw
        assert "Schema validation failed" in str(exc_info.value)

    def test_raises_schema_error_for_invalid_confidence(self) -> None:
        """Invalid confidence value raises SchemaValidationError."""
        raw = json.dumps(
            {
                "facts": [
                    {
                        "subject_entity": "Baron Aldric",
                        "text": "Some fact",
                        "category": "history",
                        "confidence": "definitely_maybe",  # Invalid
                    }
                ]
            }
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            parse_extraction_response(raw)

        assert exc_info.value.raw == raw

    def test_handles_extra_fields_gracefully(self) -> None:
        """Extra fields are ignored (Pydantic default behavior)."""
        raw = json.dumps(
            {
                "context_resolutions": [],
                "entities": [],
                "facts": [],
                "extra_field": "should be ignored",
                "another_extra": 123,
            }
        )

        result = parse_extraction_response(raw)

        assert isinstance(result, ParsedExtraction)

    def test_defaults_to_empty_arrays(self) -> None:
        """Missing optional arrays default to empty lists."""
        raw = json.dumps({})

        result = parse_extraction_response(raw)

        assert result.context_resolutions == []
        assert result.entities == []
        assert result.facts == []


# Hypothesis strategies for property-based tests

confidence_strategy = st.sampled_from([c.value for c in ConfidenceLevel])

fact_strategy = st.fixed_dictionaries(
    {
        "subject_entity": st.text(min_size=1, max_size=50),
        "text": st.text(min_size=1, max_size=500),
        "category": st.text(min_size=1, max_size=30),
        "confidence": confidence_strategy,
    },
    optional={"object_entities": st.lists(st.text(min_size=1, max_size=50))},
)

context_resolution_strategy = st.fixed_dictionaries(
    {
        "reference": st.text(min_size=1, max_size=50),
        "resolved_to": st.text(min_size=1, max_size=50),
    }
)

entity_strategy = st.fixed_dictionaries(
    {
        "entity_id": st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-0123456789"),
            min_size=1,
            max_size=30,
        ),
        "canonical_name": st.text(min_size=1, max_size=50),
        "type": st.text(min_size=1, max_size=20),
    },
    optional={"aliases": st.lists(st.text(min_size=1, max_size=30), max_size=5)},
)

valid_extraction_json_strategy = st.fixed_dictionaries(
    {},
    optional={
        "context_resolutions": st.lists(context_resolution_strategy, max_size=5),
        "entities": st.lists(entity_strategy, max_size=5),
        "facts": st.lists(fact_strategy, max_size=10),
    },
)


class TestPropertyBasedParsing:
    """Property-based tests for parser robustness."""

    @given(valid_extraction_json_strategy)
    @settings(max_examples=50)
    def test_valid_json_always_parses(self, data: dict) -> None:
        """Any valid extraction JSON parses without error."""
        raw = json.dumps(data)
        result = parse_extraction_response(raw)
        assert isinstance(result, ParsedExtraction)

    @given(valid_extraction_json_strategy)
    @settings(max_examples=50)
    def test_parsed_facts_have_valid_confidence(self, data: dict) -> None:
        """All parsed facts have valid ConfidenceLevel."""
        raw = json.dumps(data)
        result = parse_extraction_response(raw)

        for fact in result.facts:
            assert isinstance(fact.confidence, ConfidenceLevel)

    @given(valid_extraction_json_strategy)
    @settings(max_examples=50)
    def test_entity_count_preserved(self, data: dict) -> None:
        """Number of entities in input equals number in output."""
        raw = json.dumps(data)
        result = parse_extraction_response(raw)

        expected_count = len(data.get("entities", []))
        assert len(result.entities) == expected_count

    @given(valid_extraction_json_strategy)
    @settings(max_examples=50)
    def test_fact_count_preserved(self, data: dict) -> None:
        """Number of facts in input equals number in output."""
        raw = json.dumps(data)
        result = parse_extraction_response(raw)

        expected_count = len(data.get("facts", []))
        assert len(result.facts) == expected_count
