"""Procedures for merging entity-session data into per-entity data."""

from wikify.models.entity import EntityData

from .errors import EntityDataMergeIncompatibility


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
