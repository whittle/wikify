"""Error types for aggregation."""

from wikify.models.entity import EntityData


class EntityDataMergeIncompatibility(Exception):
    """Exception indicating that the attempted merge was on individually valid EntityData objects that are not jointly mergeable."""

    def __init__(self, entity_data=list[EntityData], message: str = ""):
        self.entity_data = entity_data
        super().__init__(message or "Could not merge entity data.")
