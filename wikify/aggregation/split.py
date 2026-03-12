"""Procedures for splitting an extraction into per-entity-per-session data."""

from wikify.models.entity import AggregatedFact, EntityData, Reference
from wikify.models.extraction import ExtractedEntity, ExtractionResult
from wikify.models.fact import Fact


def aggregate_fact(fact: Fact, session_num: int) -> AggregatedFact:
    return AggregatedFact(
        text=fact.text,
        category=fact.category,
        confidence=fact.confidence,
        object_entities=fact.object_entities,
        source_session=session_num,
    )


def reference_fact(fact: Fact, session_num: int) -> Reference:
    return Reference(
        source_entity=fact.subject_entity,
        fact_text=fact.text,
        source_session=session_num,
    )


def extract_facts_about_entity(
    extraction: ExtractionResult, entity_id: str
) -> list[AggregatedFact]:
    return [
        aggregate_fact(a, extraction.session_number)
        for a in extraction.facts
        if a.subject_entity == entity_id
    ]


def extract_references_to_entity(
    extraction: ExtractionResult, entity_id: str
) -> list[Reference]:
    return [
        reference_fact(a, extraction.session_number)
        for a in extraction.facts
        if entity_id in a.object_entities
    ]


def session_entity_data(
    extraction: ExtractionResult, entity: ExtractedEntity
) -> EntityData:
    return EntityData(
        entity_id=entity.entity_id,
        canonical_name=entity.canonical_name,
        aliases=entity.aliases,
        type=entity.type,
        first_appearance=entity.first_appearance,
        facts=extract_facts_about_entity(extraction, entity.entity_id),
        referenced_by=extract_references_to_entity(extraction, entity.entity_id),
        sessions_appeared=[extraction.session_number],
    )


def all_entity_data_for_session(
    extraction_result: ExtractionResult,
) -> list[EntityData]:
    return [
        session_entity_data(extraction_result, a) for a in extraction_result.entities
    ]
