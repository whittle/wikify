"""Parser for LLM extraction responses."""

import json
import re
from json import JSONDecodeError

from pydantic import BaseModel, ValidationError

from wikify.models.extraction import ContextResolution
from wikify.models.fact import Fact

from .errors import InvalidJSONError, SchemaValidationError


def _strip_code_fences(raw: str) -> str:
    """Strip markdown code fences from LLM response.

    Handles responses wrapped in ```json ... ``` or ``` ... ```.
    """
    # Match ```json or ``` at start, and ``` at end
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```\s*$"
    match = re.match(pattern, raw.strip(), re.DOTALL)
    if match:
        return match.group(1)
    return raw


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
        raw: Raw JSON string from LLM (may include markdown code fences)

    Returns:
        ParsedExtraction containing context_resolutions, entities, and facts

    Raises:
        InvalidJSONError: If the response is not valid JSON
        SchemaValidationError: If the JSON doesn't match expected schema
    """
    # Strip markdown code fences if present
    cleaned = _strip_code_fences(raw)

    try:
        data = json.loads(cleaned)
    except JSONDecodeError as e:
        raise InvalidJSONError(raw, str(e)) from e

    try:
        return ParsedExtraction.model_validate(data)
    except ValidationError as e:
        raise SchemaValidationError(raw, e.errors()) from e
