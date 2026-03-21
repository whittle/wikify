"""Fixtures for git integration tests."""

import shutil
import subprocess
import warnings
from collections.abc import Generator
from pathlib import Path

import pytest
from hypothesis import strategies as st
from hypothesis.errors import NonInteractiveExampleWarning

from wikify.models import Entity, Registry

# Strategy for generating arbitrary registries

registry_strategy = st.builds(
    Registry,
    entities=st.dictionaries(
        keys=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-"),
            min_size=1,
            max_size=30,
        ),
        values=st.builds(Entity),
        max_size=10,
    ),
)


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repo with entity-registry.json.

    Yields the path to the repo directory. Automatically cleans up
    git internals on teardown to avoid file handle issues.
    """
    repo = tmp_path / "data"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Generate and commit an arbitrary registry
    registry_file = repo / "entity-registry.json"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NonInteractiveExampleWarning)
        registry = registry_strategy.example()
    registry_file.write_text(registry.model_dump_json(indent=2))
    subprocess.run(
        ["git", "add", "entity-registry.json"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    yield repo

    # Teardown: remove .git directory to release file handles
    git_dir = repo / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
