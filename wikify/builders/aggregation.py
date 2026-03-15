"""SCons builders for aggregation (split and merge)."""

import re
from pathlib import Path
from typing import Any

from wikify.aggregation.merge import merge_entity_data
from wikify.aggregation.split import all_entity_data_for_session
from wikify.git.registry import get_data_repo_path
from wikify.models.entity import Entity, EntityData
from wikify.models.extraction import ExtractionResult
from wikify.models.registry import Registry


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
        source: List of source nodes (input extraction JSON file)
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    source_path = Path(str(source[0]))
    target_path = Path(str(target[0]))

    # Load extraction result
    extraction = ExtractionResult.model_validate_json(source_path.read_text())

    # Get all entity data for this session
    entity_data_list = all_entity_data_for_session(extraction)

    # Create target directory (parent of the marker file)
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write each entity's data to its own file
    for entity_data in entity_data_list:
        entity_file = target_dir / f"{entity_data.entity_id}.json"
        entity_file.write_text(entity_data.model_dump_json(indent=2))

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

    # Load all source EntityData files
    # Sources are expected to be sorted by session number already
    data_list = [
        EntityData.model_validate_json(Path(str(s)).read_text()) for s in source
    ]

    # Merge into single EntityData
    merged = merge_entity_data(data_list)

    # Write output
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(merged.model_dump_json(indent=2))

    return 0


def register_action(target: list[Any], source: list[Any], env: Any) -> int:
    """SCons action to register entities from an extraction into the registry.

    Args:
        target: List of target nodes (marker file .register_complete)
        source: List of source nodes (input extraction JSON file)
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    source_path = Path(str(source[0]))
    target_path = Path(str(target[0]))

    extraction = ExtractionResult.model_validate_json(source_path.read_text())

    if extraction.entities:
        registry_path = get_data_repo_path() / "entity-registry.json"
        if registry_path.exists():
            registry = Registry.model_validate_json(registry_path.read_text())
        else:
            registry = Registry()

        for extracted in extraction.entities:
            entity = Entity(
                canonical_name=extracted.canonical_name,
                aliases=extracted.aliases,
                type=extracted.type,
                first_appearance=extracted.first_appearance,
            )
            registry.merge_entity(extracted.entity_id, entity)

        registry_path.write_text(registry.model_dump_json(indent=2) + "\n")

    # Write marker file
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("")

    return 0
