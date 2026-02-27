"""Functional tests for git registry operations.

These tests use real git operations against temporary repositories,
not mocks. This ensures the git commands work correctly.
"""

import subprocess
from pathlib import Path

import pytest

from wikify.git import (
    DirtyRegistryError,
    get_data_repo_path,
    get_head_sha,
    is_file_clean,
)


class TestGetDataRepoPath:
    """Tests for get_data_repo_path."""

    def test_returns_path(self) -> None:
        """Should return a Path object."""
        result = get_data_repo_path()
        assert isinstance(result, Path)

    def test_path_ends_with_data(self) -> None:
        """Should return path ending in 'data'."""
        result = get_data_repo_path()
        assert result.name == "data"


class TestIsFileClean:
    """Tests for is_file_clean."""

    def test_clean_file_returns_true(self, temp_git_repo: Path) -> None:
        """A committed file with no changes should be clean."""
        assert is_file_clean(temp_git_repo, "entity-registry.json") is True

    def test_staged_changes_returns_false(self, temp_git_repo: Path) -> None:
        """A file with staged changes should not be clean."""
        registry = temp_git_repo / "entity-registry.json"
        registry.write_text('{"entities": {"foo": {}}}')
        subprocess.run(
            ["git", "add", "entity-registry.json"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        assert is_file_clean(temp_git_repo, "entity-registry.json") is False

    def test_unstaged_changes_returns_false(self, temp_git_repo: Path) -> None:
        """A file with unstaged changes should not be clean."""
        registry = temp_git_repo / "entity-registry.json"
        registry.write_text('{"entities": {"bar": {}}}')

        assert is_file_clean(temp_git_repo, "entity-registry.json") is False

    def test_clean_after_commit(self, temp_git_repo: Path) -> None:
        """A file should be clean again after committing changes."""
        registry = temp_git_repo / "entity-registry.json"
        registry.write_text('{"entities": {"baz": {}}}')
        subprocess.run(
            ["git", "add", "entity-registry.json"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Update registry"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        assert is_file_clean(temp_git_repo, "entity-registry.json") is True


class TestGetHeadSha:
    """Tests for get_head_sha."""

    def test_returns_40_char_sha(self, temp_git_repo: Path) -> None:
        """Should return a 40-character hexadecimal SHA."""
        sha = get_head_sha(temp_git_repo)

        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_sha_changes_after_commit(self, temp_git_repo: Path) -> None:
        """SHA should change when a new commit is made."""
        sha1 = get_head_sha(temp_git_repo)

        # Make a new commit
        registry = temp_git_repo / "entity-registry.json"
        registry.write_text('{"entities": {"new": {}}}')
        subprocess.run(
            ["git", "add", "entity-registry.json"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Second commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        sha2 = get_head_sha(temp_git_repo)

        assert sha1 != sha2
        assert len(sha2) == 40


class TestGetDataRepoCommitShaIntegration:
    """Integration tests for get_data_repo_commit_sha.

    These tests use the helper functions directly since
    get_data_repo_commit_sha uses a hardcoded path.
    """

    def test_raises_on_dirty_file(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise DirtyRegistryError when file has changes."""
        from wikify.git.registry import get_data_repo_commit_sha

        # Modify the file
        registry = temp_git_repo / "entity-registry.json"
        registry.write_text('{"entities": {"dirty": {}}}')

        # Override get_data_repo_path to use temp repo
        monkeypatch.setattr(
            "wikify.git.registry.get_data_repo_path", lambda: temp_git_repo
        )

        with pytest.raises(DirtyRegistryError) as exc_info:
            get_data_repo_commit_sha()

        assert "entity-registry.json has uncommitted changes" in str(exc_info.value)

    def test_returns_sha_when_clean(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return SHA when file is clean."""
        from wikify.git.registry import get_data_repo_commit_sha

        # Override get_data_repo_path to use temp repo
        monkeypatch.setattr(
            "wikify.git.registry.get_data_repo_path", lambda: temp_git_repo
        )

        sha = get_data_repo_commit_sha()

        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)
