"""Procedures for producing the entity data arising from a particular session."""

from wikify.models.entity import AggregatedFact, EntityData, Reference
from wikify.models.extraction import ExtractedEntity, ExtractionResult
from wikify.models.fact import Fact
from .errors import EntityDataMergeIncompatibility


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


def merge_entity_data(data: list[EntityData]) -> EntityData:
    """Merge EntityData records into a single EntityData representing everything
    known about the entity from the available data.

    Input list is order-sensitive: records are assumed to be in recency order
    with the most recent at the end of the list.

    """
    if len({(a.entity_id, a.type) for a in data}) > 1:
        raise EntityDataMergeIncompatibility(data)

    canonical_name = data[-1].canonical_name
    aliases = sorted(
        list(
            {alias for entity in data for alias in entity.aliases}
            - {data[-1].canonical_name}
        )
    )

    return EntityData(
        entity_id=data[0].entity_id,
        canonical_name=canonical_name,
        aliases=aliases,
        type=data[0].type,
        first_appearance=min([a.first_appearance for a in data]),
        facts=[fact for entity in data for fact in entity.facts],
        referenced_by=[ref for entity in data for ref in entity.referenced_by],
        sessions_appeared=sorted(
            [session for entity in data for session in entity.sessions_appeared]
        ),
    )
