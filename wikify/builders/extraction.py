"""SCons builder for session extraction."""

import re
from pathlib import Path
from typing import Any

from wikify.extraction import build_extraction_prompt, extract_session
from wikify.git.registry import get_data_repo_path
from wikify.llm.client import AnthropicClient
from wikify.models import Registry, SessionResolution


def parse_session_number(filename: str) -> int:
    """Extract session number from filename like 'session-020.txt'.

    Args:
        filename: The filename to parse

    Returns:
        The session number as an integer

    Raises:
        ValueError: If the filename doesn't match expected pattern
    """
    match = re.match(r"session-(\d+)\.txt$", filename)
    if not match:
        raise ValueError(f"Invalid session filename: {filename}")
    return int(match.group(1))


def extract_action(target: list[Any], source: list[Any], env: Any) -> int:
    """SCons action to extract a session.

    Args:
        target: List of target nodes (output JSON file)
        source: List of source nodes (input session text file)
        env: SCons environment

    Returns:
        0 on success, non-zero on failure
    """
    source_path = Path(str(source[0]))
    target_path = Path(str(target[0]))

    # Parse session number from filename
    session_number = parse_session_number(source_path.name)

    # Read session text
    session_text = source_path.read_text()

    # Load registry
    registry_path = get_data_repo_path() / "entity-registry.json"
    if registry_path.exists():
        registry = Registry.model_validate_json(registry_path.read_text())
    else:
        registry = Registry()

    # Check for optional context file
    context_path = (
        get_data_repo_path()
        / "sessions"
        / "context"
        / f"session-{session_number:03d}.txt"
    )
    context = context_path.read_text() if context_path.exists() else None

    # Build and persist prompt
    prompt = build_extraction_prompt(session_text, registry, context)
    prompt_path = (
        get_data_repo_path()
        / "sessions"
        / "prompts"
        / f"session-{session_number:03d}.txt"
    )
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt)

    # Create LLM client and extract
    client = AnthropicClient()
    result = extract_session(prompt, session_number, client)

    # Write extraction output
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(result.model_dump_json(indent=2))

    # Generate pass-through resolution file
    resolution = SessionResolution.generate_passthrough(result)
    resolution_path = (
        get_data_repo_path()
        / "sessions"
        / "resolver"
        / f"session-{session_number:03d}.json"
    )
    resolution_path.parent.mkdir(parents=True, exist_ok=True)
    resolution_path.write_text(resolution.model_dump_json(indent=2))

    return 0
