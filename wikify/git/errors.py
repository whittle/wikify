"""Error types for git operations."""


class DirtyRegistryError(Exception):
    """Raised when the entity registry has uncommitted changes."""

    pass
