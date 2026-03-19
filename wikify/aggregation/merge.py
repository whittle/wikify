"""Procedures for merging entity session data."""

from wikify.models.entity import Entity, EntityData, SessionEntityFacts


def merge_session_facts(
    entity_id: str, entity: Entity, session_facts: list[SessionEntityFacts]
) -> EntityData:
    """Merge SessionEntityFacts with entity metadata into EntityData.

    Args:
        entity_id: The entity identifier
        entity: Entity metadata from the registry
        session_facts: List of SessionEntityFacts from multiple sessions

    Returns:
        Merged EntityData ready for rendering
    """
    all_facts = [f for sf in session_facts for f in sf.facts]
    all_refs = [r for sf in session_facts for r in sf.referenced_by]
    sessions = sorted(
        {f.source_session for f in all_facts} | {r.source_session for r in all_refs}
    )

    return EntityData(
        entity_id=entity_id,
        canonical_name=entity.canonical_name,
        aliases=entity.aliases,
        type=entity.type,
        first_appearance=entity.first_appearance,
        facts=all_facts,
        referenced_by=all_refs,
        sessions_appeared=sessions,
    )
