"""Tests for extraction builder."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wikify.builders.extraction import extract_action, parse_session_number


class TestParseSessionNumber:
    """Unit tests for parse_session_number."""

    def test_single_digit(self) -> None:
        """Single digit session numbers parse correctly."""
        assert parse_session_number("session-001.txt") == 1

    def test_double_digit(self) -> None:
        """Double digit session numbers parse correctly."""
        assert parse_session_number("session-020.txt") == 20

    def test_triple_digit(self) -> None:
        """Triple digit session numbers parse correctly."""
        assert parse_session_number("session-123.txt") == 123

    def test_four_digit(self) -> None:
        """Four digit session numbers parse correctly."""
        assert parse_session_number("session-1234.txt") == 1234

    def test_leading_zeros_stripped(self) -> None:
        """Leading zeros are stripped from session numbers."""
        assert parse_session_number("session-007.txt") == 7

    def test_invalid_no_session_prefix(self) -> None:
        """Filename without 'session-' prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid session filename"):
            parse_session_number("notes-001.txt")

    def test_invalid_no_number(self) -> None:
        """Filename without number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid session filename"):
            parse_session_number("session-.txt")

    def test_invalid_wrong_extension(self) -> None:
        """Filename with wrong extension raises ValueError."""
        with pytest.raises(ValueError, match="Invalid session filename"):
            parse_session_number("session-001.json")

    def test_invalid_extra_suffix(self) -> None:
        """Filename with extra suffix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid session filename"):
            parse_session_number("session-001.txt.bak")

    def test_invalid_path_component(self) -> None:
        """Filename that's actually a path raises ValueError."""
        with pytest.raises(ValueError, match="Invalid session filename"):
            parse_session_number("sessions/session-001.txt")


class TestExtractAction:
    """Tests for extract_action SCons action."""

    @patch("wikify.builders.extraction.AnthropicClient")
    @patch("wikify.builders.extraction.extract_session")
    @patch("wikify.builders.extraction.get_data_repo_path")
    def test_writes_prompt_file(
        self,
        mock_get_data_repo_path: MagicMock,
        mock_extract_session: MagicMock,
        mock_anthropic_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """extract_action writes the interpolated prompt to prompts directory."""
        # Setup data repo structure
        data_repo = tmp_path / "data"
        sessions_raw = data_repo / "sessions" / "raw"
        sessions_raw.mkdir(parents=True)
        sessions_extracted = data_repo / "sessions" / "extracted"
        sessions_extracted.mkdir(parents=True)

        mock_get_data_repo_path.return_value = data_repo

        # Create session file
        session_file = sessions_raw / "session-007.txt"
        session_text = "The party ventured into the dark forest."
        session_file.write_text(session_text)

        # Create target file path
        target_file = sessions_extracted / "session-007.json"

        # Mock extraction result
        from wikify.models.extraction import ExtractionResult

        mock_result = ExtractionResult(
            session_number=7,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            registry_commit="abc123",
            extractor_version="1.0.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )
        mock_extract_session.return_value = mock_result

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(session_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action
        result = extract_action([target_node], [source_node], env=None)

        assert result == 0

        # Verify prompt file was written
        prompt_file = data_repo / "sessions" / "prompts" / "session-007.txt"
        assert prompt_file.exists()

        # Verify prompt contains session text and expected structure
        prompt_content = prompt_file.read_text()
        assert session_text in prompt_content
        assert "## Known Entities" in prompt_content
        assert "## Session Notes" in prompt_content

    @patch("wikify.builders.extraction.AnthropicClient")
    @patch("wikify.builders.extraction.extract_session")
    @patch("wikify.builders.extraction.get_data_repo_path")
    def test_prompt_file_includes_registry_entities(
        self,
        mock_get_data_repo_path: MagicMock,
        mock_extract_session: MagicMock,
        mock_anthropic_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Prompt file includes known entities from registry."""
        # Setup data repo structure
        data_repo = tmp_path / "data"
        sessions_raw = data_repo / "sessions" / "raw"
        sessions_raw.mkdir(parents=True)
        sessions_extracted = data_repo / "sessions" / "extracted"
        sessions_extracted.mkdir(parents=True)

        mock_get_data_repo_path.return_value = data_repo

        # Create registry with an entity
        registry_data = {
            "entities": {
                "baron-aldric": {
                    "canonical_name": "Baron Aldric",
                    "aliases": ["the Baron", "Lord Aldric"],
                    "type": "person",
                    "first_appearance": 1,
                    "description": "local liege lord",
                }
            }
        }
        registry_file = data_repo / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create session file
        session_file = sessions_raw / "session-020.txt"
        session_file.write_text("We met with the Baron.")

        # Create target file path
        target_file = sessions_extracted / "session-020.json"

        # Mock extraction result
        from wikify.models.extraction import ExtractionResult

        mock_result = ExtractionResult(
            session_number=20,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            registry_commit="abc123",
            extractor_version="1.0.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )
        mock_extract_session.return_value = mock_result

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(session_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action
        extract_action([target_node], [source_node], env=None)

        # Verify prompt file includes registry entity
        prompt_file = data_repo / "sessions" / "prompts" / "session-020.txt"
        prompt_content = prompt_file.read_text()
        assert "baron-aldric" in prompt_content
        assert "Baron Aldric" in prompt_content
        assert "the Baron" in prompt_content

    @patch("wikify.builders.extraction.AnthropicClient")
    @patch("wikify.builders.extraction.extract_session")
    @patch("wikify.builders.extraction.get_data_repo_path")
    def test_missing_context_file_works(
        self,
        mock_get_data_repo_path: MagicMock,
        mock_extract_session: MagicMock,
        mock_anthropic_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Extraction works when context file does not exist."""
        # Setup data repo structure
        data_repo = tmp_path / "data"
        sessions_raw = data_repo / "sessions" / "raw"
        sessions_raw.mkdir(parents=True)
        sessions_extracted = data_repo / "sessions" / "extracted"
        sessions_extracted.mkdir(parents=True)

        mock_get_data_repo_path.return_value = data_repo

        # Create session file (no context file)
        session_file = sessions_raw / "session-005.txt"
        session_file.write_text("The party explored.")

        # Create target file path
        target_file = sessions_extracted / "session-005.json"

        # Mock extraction result
        from wikify.models.extraction import ExtractionResult

        mock_result = ExtractionResult(
            session_number=5,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            registry_commit="abc123",
            extractor_version="1.0.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )
        mock_extract_session.return_value = mock_result

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(session_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action
        result = extract_action([target_node], [source_node], env=None)

        assert result == 0

        # Verify prompt file exists and does not have context section
        prompt_file = data_repo / "sessions" / "prompts" / "session-005.txt"
        prompt_content = prompt_file.read_text()
        assert "## Session Context" not in prompt_content

    @patch("wikify.builders.extraction.AnthropicClient")
    @patch("wikify.builders.extraction.extract_session")
    @patch("wikify.builders.extraction.get_data_repo_path")
    def test_context_file_is_read_and_included(
        self,
        mock_get_data_repo_path: MagicMock,
        mock_extract_session: MagicMock,
        mock_anthropic_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Context file content is included in the prompt."""
        # Setup data repo structure
        data_repo = tmp_path / "data"
        sessions_raw = data_repo / "sessions" / "raw"
        sessions_raw.mkdir(parents=True)
        sessions_extracted = data_repo / "sessions" / "extracted"
        sessions_extracted.mkdir(parents=True)
        sessions_context = data_repo / "sessions" / "context"
        sessions_context.mkdir(parents=True)

        mock_get_data_repo_path.return_value = data_repo

        # Create session file
        session_file = sessions_raw / "session-012.txt"
        session_file.write_text("We climbed the mountain at dawn.")

        # Create context file
        context_file = sessions_context / "session-012.txt"
        context_text = "The mountain refers to Mount Tambora from session 3."
        context_file.write_text(context_text)

        # Create target file path
        target_file = sessions_extracted / "session-012.json"

        # Mock extraction result
        from wikify.models.extraction import ExtractionResult

        mock_result = ExtractionResult(
            session_number=12,
            extracted_at=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            registry_commit="abc123",
            extractor_version="1.0.0",
            context_resolutions=[],
            entities=[],
            facts=[],
        )
        mock_extract_session.return_value = mock_result

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(session_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action
        result = extract_action([target_node], [source_node], env=None)

        assert result == 0

        # Verify prompt file includes context
        prompt_file = data_repo / "sessions" / "prompts" / "session-012.txt"
        prompt_content = prompt_file.read_text()
        assert "## Session Context" in prompt_content
        assert context_text in prompt_content
