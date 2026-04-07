"""Procedures for splitting an extraction into per-entity-per-session data."""

from wikify.models import (
    AggregatedFact,
    Fact,
    Reference,
    ResolvedExtraction,
    SessionEntityFacts,
)


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
    extraction: ResolvedExtraction, entity_id: str
) -> list[AggregatedFact]:
    return [
        aggregate_fact(a, extraction.session_number)
        for a in extraction.facts
        if a.subject_entity == entity_id
    ]


def extract_references_to_entity(
    extraction: ResolvedExtraction, entity_id: str
) -> list[Reference]:
    return [
        reference_fact(a, extraction.session_number)
        for a in extraction.facts
        if entity_id in a.object_entities
    ]


def session_facts_for_entity(
    extraction: ResolvedExtraction, entity_id: str
) -> SessionEntityFacts:
    """Create SessionEntityFacts for an entity from this session."""
    return SessionEntityFacts(
        entity_id=entity_id,
        facts=extract_facts_about_entity(extraction, entity_id),
        referenced_by=extract_references_to_entity(extraction, entity_id),
    )


def all_session_facts(extraction: ResolvedExtraction) -> list[SessionEntityFacts]:
    """Get SessionEntityFacts for all entities referenced in this session's facts."""
    entity_ids: set[str] = set()
    for fact in extraction.facts:
        entity_ids.add(fact.subject_entity)
        entity_ids.update(fact.object_entities)

    return [session_facts_for_entity(extraction, eid) for eid in entity_ids]
