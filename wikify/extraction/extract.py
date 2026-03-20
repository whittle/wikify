"""Session extraction orchestration."""

from datetime import datetime, timezone

from wikify.git.registry import get_data_repo_commit_sha
from wikify.llm.client import LLMClient
from wikify.models.extraction import ExtractedEntity, ExtractionResult

from .parser import parse_extraction_response

EXTRACTOR_VERSION = "0.1.0"


def extract_session(
    prompt: str,
    session_number: int,
    client: LLMClient,
) -> ExtractionResult:
    """Extract facts from session notes.

    Orchestrates the full extraction workflow:
    1. Verify registry is clean via get_data_repo_commit_sha()
    2. Call LLM with provided prompt
    3. Parse response into structured data
    4. Convert RawExtractedEntity → ExtractedEntity (set first_appearance)
    5. Assemble ExtractionResult with metadata

    Args:
        prompt: The fully-built extraction prompt (including session text,
            registry entities, and optional context)
        session_number: The session number (e.g., 7 for session-007.txt)
        client: LLM client for generating extraction

    Returns:
        ExtractionResult with extracted facts, entities, and metadata

    Raises:
        DirtyRegistryError: If the entity registry has uncommitted changes
        InvalidJSONError: If the LLM response is not valid JSON
        SchemaValidationError: If the LLM response doesn't match expected schema
    """
    # Step 1: Verify registry is clean and get commit SHA
    registry_commit = get_data_repo_commit_sha()

    # Step 2: Call LLM
    raw_response = client.complete(prompt)

    # Step 4: Parse response
    parsed = parse_extraction_response(raw_response)

    # Step 5: Convert RawExtractedEntity → ExtractedEntity
    entities = [
        ExtractedEntity(
            entity_id=raw_entity.entity_id,
            canonical_name=raw_entity.canonical_name,
            aliases=raw_entity.aliases,
            type=raw_entity.type,
            first_appearance=session_number,
        )
        for raw_entity in parsed.entities
    ]

    # Step 6: Assemble ExtractionResult with metadata
    return ExtractionResult(
        session_number=session_number,
        extracted_at=datetime.now(timezone.utc),
        registry_commit=registry_commit,
        extractor_version=EXTRACTOR_VERSION,
        context_resolutions=parsed.context_resolutions,
        entities=entities,
        facts=parsed.facts,
    )
