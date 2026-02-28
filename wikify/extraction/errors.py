"""Error types for extraction parsing."""

from typing import Any


class ExtractionParseError(Exception):
    """Base exception for extraction parsing failures."""

    def __init__(self, raw: str, message: str = "") -> None:
        self.raw = raw
        super().__init__(message or "Failed to parse extraction response")


class InvalidJSONError(ExtractionParseError):
    """Raised when the LLM response is not valid JSON."""

    def __init__(self, raw: str, json_error: str) -> None:
        self.json_error = json_error
        super().__init__(raw, f"Invalid JSON: {json_error}")


class SchemaValidationError(ExtractionParseError):
    """Raised when JSON doesn't match expected schema."""

    def __init__(self, raw: str, validation_errors: list[Any]) -> None:
        self.validation_errors = validation_errors
        error_summary = "; ".join(
            f"{e.get('loc', 'unknown')}: {e.get('msg', 'validation error')}"
            for e in validation_errors
        )
        super().__init__(raw, f"Schema validation failed: {error_summary}")
