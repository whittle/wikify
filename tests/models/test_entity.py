"""Tests for Entity and EntityData models."""

from datetime import datetime


from wikify.models import (
    AggregatedFact,
    ConfidenceLevel,
    Entity,
    EntityData,
    Reference,
)


class TestEntity:
    def test_minimal_entity(self):
        """Entity can be created with required fields."""
        entity = Entity(
            canonical_name="Baron Aldric",
            type="person",
            first_appearance=1,
        )
        assert entity.canonical_name == "Baron Aldric"
        assert entity.aliases == []
        assert entity.type == "person"
        assert entity.first_appearance == 1

    def test_entity_with_aliases(self):
        """Entity can have multiple aliases."""
        entity = Entity(
            canonical_name="Mount Tambora",
            aliases=["The Mountain", "Tambora", "The Sleeping Giant"],
            type="location",
            first_appearance=3,
        )
        assert len(entity.aliases) == 3
        assert "The Mountain" in entity.aliases

    def test_entity_serialization(self):
        """Entity serializes to JSON correctly."""
        entity = Entity(
            canonical_name="The Oracle",
            aliases=["Seer"],
            type="person",
            first_appearance=5,
        )
        data = entity.model_dump()
        assert data == {
            "canonical_name": "The Oracle",
            "aliases": ["Seer"],
            "type": "person",
            "first_appearance": 5,
        }

    def test_entity_type_is_freeform(self):
        """Entity type is not constrained to a fixed set."""
        entity = Entity(
            canonical_name="The Curse of Ages",
            type="phenomenon",
            first_appearance=7,
        )
        assert entity.type == "phenomenon"

        entity2 = Entity(
            canonical_name="The Silver Blade",
            type="artifact",
            first_appearance=2,
        )
        assert entity2.type == "artifact"


class TestAggregatedFact:
    def test_aggregated_fact(self):
        """AggregatedFact includes source session."""
        fact = AggregatedFact(
            text="Baron Aldric declared war.",
            category="history",
            confidence=ConfidenceLevel.STATED,
            source_session=5,
        )
        assert fact.source_session == 5
        assert fact.object_entities == []


class TestReference:
    def test_reference(self):
        """Reference tracks facts from other entities."""
        ref = Reference(
            source_entity="Baron Aldric",
            fact_text="Baron Aldric visited Thornwood.",
            source_session=3,
        )
        assert ref.source_entity == "Baron Aldric"
        assert ref.source_session == 3


class TestEntityData:
    def test_entity_data_minimal(self):
        """EntityData can be created with minimal fields."""
        now = datetime.now()
        data = EntityData(
            entity_id="baron-aldric",
            canonical_name="Baron Aldric",
            type="person",
            first_appearance=1,
            last_updated=now,
        )
        assert data.entity_id == "baron-aldric"
        assert data.facts == []
        assert data.referenced_by == []
        assert data.sessions_appeared == []

    def test_entity_data_full(self):
        """EntityData can contain facts and references."""
        now = datetime.now()
        data = EntityData(
            entity_id="thornwood",
            canonical_name="Thornwood",
            aliases=["The Dark Forest"],
            type="location",
            first_appearance=2,
            facts=[
                AggregatedFact(
                    text="Thornwood is haunted.",
                    category="lore",
                    confidence=ConfidenceLevel.RUMOR,
                    source_session=2,
                ),
            ],
            referenced_by=[
                Reference(
                    source_entity="Baron Aldric",
                    fact_text="Baron Aldric avoids Thornwood.",
                    source_session=3,
                ),
            ],
            sessions_appeared=[2, 3, 5],
            last_updated=now,
        )
        assert len(data.facts) == 1
        assert len(data.referenced_by) == 1
        assert data.sessions_appeared == [2, 3, 5]

    def test_entity_data_serialization_roundtrip(self):
        """EntityData can be serialized and deserialized."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        original = EntityData(
            entity_id="test-entity",
            canonical_name="Test Entity",
            type="object",
            first_appearance=1,
            last_updated=now,
        )
        json_data = original.model_dump_json()
        restored = EntityData.model_validate_json(json_data)
        assert restored.entity_id == original.entity_id
        assert restored.last_updated == original.last_updated
