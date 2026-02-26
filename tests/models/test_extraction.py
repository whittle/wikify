"""Tests for extraction result models."""

from datetime import datetime

from pipeline.models import (
    ConfidenceLevel,
    ContextResolution,
    ExtractedEntity,
    ExtractionResult,
    Fact,
)


class TestContextResolution:
    def test_context_resolution(self):
        """ContextResolution maps references to canonical entities."""
        resolution = ContextResolution(
            reference="the mountain",
            resolved_to="Mount Tambora",
        )
        assert resolution.reference == "the mountain"
        assert resolution.resolved_to == "Mount Tambora"


class TestExtractedEntity:
    def test_extracted_entity(self):
        """ExtractedEntity captures entity discovery."""
        entity = ExtractedEntity(
            entity_id="baron-aldric",
            canonical_name="Baron Aldric",
            aliases=["The Baron", "Lord Aldric"],
            type="person",
            first_appearance=1,
        )
        assert entity.entity_id == "baron-aldric"
        assert len(entity.aliases) == 2


class TestExtractionResult:
    def test_extraction_result_minimal(self):
        """ExtractionResult can be created with required fields."""
        result = ExtractionResult(
            session_number=1,
            extracted_at=datetime.now(),
            registry_commit="abc123",
            extractor_version="1.0.0",
        )
        assert result.session_number == 1
        assert result.context_resolutions == []
        assert result.entities == []
        assert result.facts == []

    def test_extraction_result_full(self):
        """ExtractionResult can contain all data types."""
        now = datetime.now()
        result = ExtractionResult(
            session_number=5,
            extracted_at=now,
            registry_commit="def456",
            extractor_version="1.0.0",
            context_resolutions=[
                ContextResolution(
                    reference="the mountain",
                    resolved_to="Mount Tambora",
                ),
            ],
            entities=[
                ExtractedEntity(
                    entity_id="sera",
                    canonical_name="Sera",
                    type="person",
                    first_appearance=5,
                ),
            ],
            facts=[
                Fact(
                    subject_entity="Sera",
                    text="Sera is a ranger.",
                    category="occupation",
                    confidence=ConfidenceLevel.STATED,
                ),
            ],
        )
        assert len(result.context_resolutions) == 1
        assert len(result.entities) == 1
        assert len(result.facts) == 1

    def test_extraction_result_serialization_roundtrip(self):
        """ExtractionResult can be serialized and deserialized."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        original = ExtractionResult(
            session_number=3,
            extracted_at=now,
            registry_commit="abc123def456",
            extractor_version="1.0.0",
            facts=[
                Fact(
                    subject_entity="Test",
                    text="Test fact.",
                    category="test",
                    confidence=ConfidenceLevel.STATED,
                ),
            ],
        )
        json_data = original.model_dump_json()
        restored = ExtractionResult.model_validate_json(json_data)
        assert restored.session_number == 3
        assert restored.registry_commit == "abc123def456"
        assert len(restored.facts) == 1
        assert restored.facts[0].confidence == ConfidenceLevel.STATED
