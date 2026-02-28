"""Parser for LLM extraction responses."""

import json
from json import JSONDecodeError

from pydantic import BaseModel, ValidationError

from wikify.models.extraction import ContextResolution
from wikify.models.fact import Fact

from .errors import InvalidJSONError, SchemaValidationError


class RawExtractedEntity(BaseModel):
    """New entity discovered by LLM (no first_appearance - always current session)."""

    entity_id: str
    canonical_name: str
    aliases: list[str] = []
    type: str


class ParsedExtraction(BaseModel):
    """Intermediate result from parsing LLM output."""

    context_resolutions: list[ContextResolution] = []
    entities: list[RawExtractedEntity] = []
    facts: list[Fact] = []


def parse_extraction_response(raw: str) -> ParsedExtraction:
    """Parse LLM JSON response into structured extraction data.

    Args:
        raw: Raw JSON string from LLM

    Returns:
        ParsedExtraction containing context_resolutions, entities, and facts

    Raises:
        InvalidJSONError: If the response is not valid JSON
        SchemaValidationError: If the JSON doesn't match expected schema
    """
    try:
        data = json.loads(raw)
    except JSONDecodeError as e:
        raise InvalidJSONError(raw, str(e)) from e

    try:
        return ParsedExtraction.model_validate(data)
    except ValidationError as e:
        raise SchemaValidationError(raw, e.errors()) from e
