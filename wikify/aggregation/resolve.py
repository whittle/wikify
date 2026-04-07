"""Load and resolve extractions through SessionResolution."""

from pathlib import Path

from wikify.models import ExtractionResult, ResolvedExtraction, SessionResolution


def load_resolved_extraction(
    extraction_path: Path,
    resolution_path: Path,
) -> ResolvedExtraction:
    """Load extraction and resolution, return resolved result.

    Args:
        extraction_path: Path to the extraction JSON file
        resolution_path: Path to the resolution JSON file

    Returns:
        ResolvedExtraction with all entity_ids translated through resolution

    Raises:
        KeyError: If any entity_id in extraction is missing from resolution
    """
    extraction = ExtractionResult.model_validate_json(extraction_path.read_text())
    resolution = SessionResolution.model_validate_json(resolution_path.read_text())

    return ResolvedExtraction.from_extraction_and_resolution(extraction, resolution)
