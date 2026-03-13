# -*- mode: python -*-
"""SCons build configuration for wikify pipeline."""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, Dir(".").abspath)

from wikify.scons import (
    create_extraction_builder,
    create_merge_builder,
    create_split_builder,
    get_data_repo_path,
    init_wikify,
)

env = Environment()
init_wikify(env.Dictionary(as_dict=True))
env.Append(BUILDERS={
    "Extract": create_extraction_builder(env),
    "Split": create_split_builder(env),
    "Merge": create_merge_builder(env),
})

# Command-line options
AddOption(
    "--session",
    dest="session",
    type="int",
    metavar="N",
    help="Session number to extract (e.g., --session=20)",
)


def discover_entity_sources(sessions_dir: Path) -> dict[str, list[Path]]:
    """Discover all entity JSON files across session splits.

    Returns:
        Dict mapping entity_id to list of source files, sorted by session number.
    """
    entity_sources: dict[str, list[tuple[int, Path]]] = {}

    for session_dir in sorted(sessions_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        # Parse session number from directory name
        match = __import__("re").match(r"session-(\d+)$", session_dir.name)
        if not match:
            continue
        session_num = int(match.group(1))

        for entity_file in session_dir.glob("*.json"):
            entity_id = entity_file.stem
            if entity_id not in entity_sources:
                entity_sources[entity_id] = []
            entity_sources[entity_id].append((session_num, entity_file))

    # Sort by session number and return just the paths
    return {
        entity_id: [path for _, path in sorted(sources)]
        for entity_id, sources in entity_sources.items()
    }


# Build targets based on options
data_path = get_data_repo_path()
registry_path = data_path / "entity-registry.json"
sessions_dir = data_path / "entities" / "sessions"
entity_data_dir = data_path / "entities" / "data"

session_num = GetOption("session")
if session_num:
    # Extraction
    raw_source = data_path / "sessions" / "raw" / f"session-{session_num:03d}.txt"
    extraction_target = data_path / "sessions" / "extracted" / f"session-{session_num:03d}.json"

    extraction = env.Extract(str(extraction_target), str(raw_source))
    env.Depends(extraction, str(registry_path))

    # Split (depends on extraction)
    split_marker = sessions_dir / f"session-{session_num:03d}" / ".split_complete"
    split = env.Split(str(split_marker), str(extraction_target))
    env.Depends(split, extraction)

# Always set up merge targets for existing split outputs
if sessions_dir.exists():
    entity_sources = discover_entity_sources(sessions_dir)
    for entity_id, source_files in entity_sources.items():
        merge_target = entity_data_dir / f"{entity_id}.json"
        source_strs = [str(f) for f in source_files]

        merge = env.Merge(str(merge_target), source_strs)

        # Merge depends on all split marker files for sessions that have this entity
        for source_file in source_files:
            marker = source_file.parent / ".split_complete"
            if marker.exists():
                env.Depends(merge, str(marker))
