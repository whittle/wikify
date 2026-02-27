"""Git operations for entity registry verification."""

import subprocess
from pathlib import Path

from .errors import DirtyRegistryError


def get_data_repo_path() -> Path:
    """Return the path to the data submodule.

    Currently hardcoded to `data/` relative to project root.
    """
    return Path(__file__).parent.parent.parent / "data"


def is_file_clean(repo_path: Path, filename: str) -> bool:
    """Check if a file has uncommitted changes in the given repo.

    Args:
        repo_path: Path to the git repository
        filename: Name of the file to check

    Returns:
        True if the file is clean (committed, no changes), False otherwise
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", filename],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == ""


def get_head_sha(repo_path: Path) -> str:
    """Return the HEAD commit SHA for the given repo.

    Args:
        repo_path: Path to the git repository

    Returns:
        The full 40-character SHA of HEAD
    """
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_data_repo_commit_sha(filename: str = "entity-registry.json") -> str:
    """Return commit SHA of data repo if file is clean, raise if dirty.

    Args:
        filename: The file to check for cleanliness (default: entity-registry.json)

    Returns:
        The commit SHA of the data repository HEAD

    Raises:
        DirtyRegistryError: If the file has uncommitted changes
    """
    repo_path = get_data_repo_path()
    if not is_file_clean(repo_path, filename):
        raise DirtyRegistryError(f"{filename} has uncommitted changes")
    return get_head_sha(repo_path)
