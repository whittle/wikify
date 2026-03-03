"""Tests for extraction response parser."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wikify.extraction.errors import InvalidJSONError, SchemaValidationError
from wikify.extraction.parser import (
    ParsedExtraction,
    _strip_code_fences,
    parse_extraction_response,
)
from wikify.models.fact import ConfidenceLevel


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


class TestStripCodeFences:
    @given(valid_extraction_json_strategy)
    def test_strips_json_code_fence(self, data) -> None:
        actual = json.dumps(data)

        result = _strip_code_fences(f"```json\n{actual}\n```")

        assert result == actual

    @given(valid_extraction_json_strategy)
    def test_strips_plain_code_fence(self, data) -> None:
        actual = json.dumps(data)

        result = _strip_code_fences(f"```\n{actual}\n```")

        assert result == actual

    @given(valid_extraction_json_strategy)
    def test_preserves_plain_json(self, data) -> None:
        actual = json.dumps(data)

        result = _strip_code_fences(actual)

        assert result == actual

    @given(valid_extraction_json_strategy)
    def test_handles_whitespace(self, data) -> None:
        """Handles leading/trailing whitespace around fences."""
        actual = json.dumps(data)

        result = _strip_code_fences(f" \n ```json\n{actual}\n```  ")

        assert result == actual


class TestParseExtractionResponse:
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

    def test_parses_json_wrapped_in_code_fence(self) -> None:
        """JSON wrapped in markdown code fences parses correctly."""
        raw = '```json\n{"context_resolutions": [], "entities": [], "facts": []}\n```'
        result = parse_extraction_response(raw)

        assert result.context_resolutions == []
        assert result.entities == []
        assert result.facts == []

    def test_error_message_includes_received_content(self) -> None:
        """InvalidJSONError message includes the received content."""
        raw = "This is not JSON but some other text"

        with pytest.raises(InvalidJSONError) as exc_info:
            parse_extraction_response(raw)

        error_message = str(exc_info.value)
        assert "Received:" in error_message
        assert "This is not JSON" in error_message

    def test_error_message_truncates_long_content(self) -> None:
        """InvalidJSONError truncates very long received content."""
        raw = "x" * 500  # 500 characters of invalid content

        with pytest.raises(InvalidJSONError) as exc_info:
            parse_extraction_response(raw)

        error_message = str(exc_info.value)
        assert "..." in error_message
        # Should be truncated to ~200 chars + "..."
        assert len(error_message) < 400
