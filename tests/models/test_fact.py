"""Tests for the Fact model and ConfidenceLevel enum."""

import pytest
from pydantic import ValidationError

from pipeline.models import ConfidenceLevel, Fact


class TestConfidenceLevel:
    def test_all_levels_have_string_values(self):
        """Each confidence level should have a meaningful string value."""
        expected = {
            "stated",
            "observed",
            "character_claim",
            "implied",
            "rumor",
            "player_theory",
            "uncertain",
            "superseded",
        }
        actual = {level.value for level in ConfidenceLevel}
        assert actual == expected

    def test_confidence_level_is_string_enum(self):
        """ConfidenceLevel values should be usable as strings."""
        assert ConfidenceLevel.STATED == "stated"
        assert ConfidenceLevel.RUMOR.value == "rumor"


class TestFact:
    def test_minimal_fact(self):
        """Fact can be created with just required fields."""
        fact = Fact(
            subject_entity="Baron Aldric",
            text="Baron Aldric rules the northern province.",
            category="politics",
            confidence=ConfidenceLevel.STATED,
        )
        assert fact.subject_entity == "Baron Aldric"
        assert fact.object_entities == []
        assert fact.text == "Baron Aldric rules the northern province."
        assert fact.category == "politics"
        assert fact.confidence == ConfidenceLevel.STATED

    def test_fact_with_object_entities(self):
        """Fact can reference multiple object entities."""
        fact = Fact(
            subject_entity="Baron Aldric",
            object_entities=["Thornwood", "Lady Mira"],
            text="Baron Aldric met Lady Mira in Thornwood.",
            category="history",
            confidence=ConfidenceLevel.OBSERVED,
        )
        assert fact.object_entities == ["Thornwood", "Lady Mira"]

    def test_fact_serialization(self):
        """Fact serializes to JSON correctly."""
        fact = Fact(
            subject_entity="Mount Tambora",
            text="Mount Tambora is an active volcano.",
            category="geography",
            confidence=ConfidenceLevel.STATED,
        )
        data = fact.model_dump()
        assert data["subject_entity"] == "Mount Tambora"
        assert data["confidence"] == "stated"

    def test_fact_deserialization(self):
        """Fact deserializes from JSON correctly."""
        data = {
            "subject_entity": "The Oracle",
            "object_entities": [],
            "text": "The Oracle speaks in riddles.",
            "category": "abilities",
            "confidence": "character_claim",
        }
        fact = Fact(**data)
        assert fact.confidence == ConfidenceLevel.CHARACTER_CLAIM

    def test_fact_requires_subject_entity(self):
        """Fact must have a subject_entity."""
        with pytest.raises(ValidationError):
            Fact(
                text="Some fact without a subject.",
                category="misc",
                confidence=ConfidenceLevel.UNCERTAIN,
            )

    def test_fact_requires_text(self):
        """Fact must have text content."""
        with pytest.raises(ValidationError):
            Fact(
                subject_entity="Someone",
                category="misc",
                confidence=ConfidenceLevel.UNCERTAIN,
            )

    def test_invalid_confidence_level(self):
        """Invalid confidence level raises validation error."""
        with pytest.raises(ValidationError):
            Fact(
                subject_entity="Someone",
                text="Some fact.",
                category="misc",
                confidence="invalid_level",
            )
