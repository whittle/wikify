"""SCons builders for aggregation (split and merge)."""

import re
from pathlib import Path
from typing import Any

from wikify.aggregation.errors import EntityMismatchError, EntityNotFoundError
from wikify.aggregation.merge import merge_session_facts
from wikify.aggregation.resolve import load_resolved_extraction
from wikify.aggregation.split import all_session_facts
from wikify.git.registry import get_data_repo_path
from wikify.models import Entity, Registry, SessionEntityFacts


def parse_session_number_from_json(filename: str) -> int:
    """Extract session number from filename like 'session-020.json'.

    Args:
        filename: The filename to parse

    Returns:
        The session number as an integer

    Raises:
        ValueError: If the filename doesn't match expected pattern
    """
    match = re.match(r"session-(\d+)\.json$", filename)
    if not match:
        raise ValueError(f"Invalid extraction filename: {filename}")
    return int(match.group(1))


def split_action(target: list[Any], source: list[Any], env: Any) -> int:
    """SCons action to split an extraction into per-entity session files.

    Args:
        target: List of target nodes (marker file .split_complete)
        source: List of source nodes [extraction JSON, resolution JSON]
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    extraction_path = Path(str(source[0]))
    resolution_path = Path(str(source[1]))
    target_path = Path(str(target[0]))

    # Load and resolve extraction
    resolved = load_resolved_extraction(extraction_path, resolution_path)

    # Get all session facts for this session
    session_facts_list = all_session_facts(resolved)

    # Create target directory (parent of the marker file)
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write each entity's facts to its own file
    for session_facts in session_facts_list:
        entity_file = target_dir / f"{session_facts.entity_id}.json"
        entity_file.write_text(session_facts.model_dump_json(indent=2))

    # Write marker file to signal completion
    target_path.write_text("")

    return 0


def merge_action(target: list[Any], source: list[Any], env: Any) -> int:
    """SCons action to merge entity-session files into a single entity data file.

    Args:
        target: List of target nodes (output entity data JSON file)
        source: List of source nodes (input entity-session JSON files, sorted by session)
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    target_path = Path(str(target[0]))
    entity_id = target_path.stem  # e.g., "baron-aldric"

    # Load registry for entity metadata
    registry_path = get_data_repo_path() / "entity-registry.json"
    registry = Registry.model_validate_json(registry_path.read_text())
    entity = registry.get_entity(entity_id)
    if entity is None:
        raise EntityNotFoundError(entity_id)

    # Load all session facts
    session_facts = [
        SessionEntityFacts.model_validate_json(Path(str(s)).read_text()) for s in source
    ]

    # Validate all session facts are for the expected entity
    for sf in session_facts:
        if sf.entity_id != entity_id:
            raise EntityMismatchError(entity_id, sf.entity_id)

    # Merge into EntityData
    merged = merge_session_facts(entity_id, entity, session_facts)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(merged.model_dump_json(indent=2))
    return 0


def register_action(target: list[Any], source: list[Any], env: Any) -> int:
    """SCons action to register entities from an extraction into the registry.

    Args:
        target: List of target nodes (marker file .register_complete)
        source: List of source nodes [extraction JSON, resolution JSON]
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    extraction_path = Path(str(source[0]))
    resolution_path = Path(str(source[1]))
    target_path = Path(str(target[0]))

    resolved = load_resolved_extraction(extraction_path, resolution_path)

    if resolved.entities:
        registry_path = get_data_repo_path() / "entity-registry.json"
        if registry_path.exists():
            registry = Registry.model_validate_json(registry_path.read_text())
        else:
            registry = Registry()

        for extracted in resolved.entities:
            entity = Entity(
                canonical_name=extracted.canonical_name,
                aliases=extracted.aliases,
                type=extracted.type,
                first_appearance=extracted.first_appearance,
                description=None,
            )
            registry.merge_entity(extracted.entity_id, entity)

        registry_path.write_text(registry.model_dump_json(indent=2) + "\n")

    # Write marker file
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("")

    return 0
