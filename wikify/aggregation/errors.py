"""Error types for aggregation."""


class EntityNotFoundError(Exception):
    """Raised when an entity_id is not found in the registry."""

    def __init__(self, entity_id: str, message: str = ""):
        self.entity_id = entity_id
        super().__init__(message or f"Entity '{entity_id}' not found in registry.")


class EntityMismatchError(Exception):
    """Raised when a SessionEntityFacts has a different entity_id than expected."""

    def __init__(self, expected: str, actual: str, message: str = ""):
        self.expected = expected
        self.actual = actual
        super().__init__(
            message
            or f"Expected entity_id '{expected}', but found '{actual}' in session facts."
        )
