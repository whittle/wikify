"""Tests for aggregation builders."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wikify.aggregation.errors import EntityMismatchError, EntityNotFoundError
from wikify.builders.aggregation import (
    merge_action,
    parse_session_number_from_json,
    register_action,
    split_action,
)


class TestParseSessionNumberFromJson:
    """Unit tests for parse_session_number_from_json."""

    def test_single_digit(self) -> None:
        """Single digit session numbers parse correctly."""
        assert parse_session_number_from_json("session-001.json") == 1

    def test_double_digit(self) -> None:
        """Double digit session numbers parse correctly."""
        assert parse_session_number_from_json("session-020.json") == 20

    def test_triple_digit(self) -> None:
        """Triple digit session numbers parse correctly."""
        assert parse_session_number_from_json("session-123.json") == 123

    def test_leading_zeros_stripped(self) -> None:
        """Leading zeros are stripped from session numbers."""
        assert parse_session_number_from_json("session-007.json") == 7

    def test_invalid_no_session_prefix(self) -> None:
        """Filename without 'session-' prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid extraction filename"):
            parse_session_number_from_json("notes-001.json")

    def test_invalid_wrong_extension(self) -> None:
        """Filename with wrong extension raises ValueError."""
        with pytest.raises(ValueError, match="Invalid extraction filename"):
            parse_session_number_from_json("session-001.txt")


class TestSplitAction:
    """Tests for split_action SCons action."""

    def test_creates_session_entity_facts_files(self, tmp_path: Path) -> None:
        """split_action creates SessionEntityFacts files for each entity."""
        # Create extraction file
        extracted_dir = tmp_path / "sessions" / "extracted"
        extracted_dir.mkdir(parents=True)
        extraction_data = {
            "session_number": 5,
            "extracted_at": "2024-01-01T00:00:00Z",
            "registry_commit": "abc123",
            "extractor_version": "1.0.0",
            "context_resolutions": [],
            "entities": [],
            "facts": [
                {
                    "subject_entity": "baron-aldric",
                    "object_entities": ["thornwood"],
                    "text": "Baron Aldric visited Thornwood.",
                    "category": "history",
                    "confidence": "stated",
                }
            ],
        }
        extraction_file = extracted_dir / "session-005.json"
        extraction_file.write_text(json.dumps(extraction_data))

        # Create target directory and marker file path
        session_dir = tmp_path / "entities" / "sessions" / "session-005"
        marker_file = session_dir / ".split_complete"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(extraction_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(marker_file))

        # Run action
        result = split_action([target_node], [source_node], env=None)

        assert result == 0
        assert marker_file.exists()

        # Check entity files were created
        baron_file = session_dir / "baron-aldric.json"
        thornwood_file = session_dir / "thornwood.json"
        assert baron_file.exists()
        assert thornwood_file.exists()

        # Verify baron file content
        baron_data = json.loads(baron_file.read_text())
        assert baron_data["entity_id"] == "baron-aldric"
        assert len(baron_data["facts"]) == 1
        assert baron_data["facts"][0]["text"] == "Baron Aldric visited Thornwood."

        # Verify thornwood file content (referenced, no facts as subject)
        thornwood_data = json.loads(thornwood_file.read_text())
        assert thornwood_data["entity_id"] == "thornwood"
        assert len(thornwood_data["facts"]) == 0
        assert len(thornwood_data["referenced_by"]) == 1


class TestMergeAction:
    """Tests for merge_action SCons action."""

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_merges_session_facts_into_entity_data(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """merge_action combines SessionEntityFacts with registry metadata."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create registry
        registry_data = {
            "entities": {
                "baron-aldric": {
                    "canonical_name": "Baron Aldric",
                    "aliases": ["the Baron"],
                    "type": "person",
                    "first_appearance": 3,
                    "description": None,
                }
            }
        }
        registry_file = tmp_path / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create session entity facts files
        session_005_dir = tmp_path / "entities" / "sessions" / "session-005"
        session_005_dir.mkdir(parents=True)
        session_010_dir = tmp_path / "entities" / "sessions" / "session-010"
        session_010_dir.mkdir(parents=True)

        session_005_facts = {
            "entity_id": "baron-aldric",
            "facts": [
                {
                    "text": "Baron Aldric visited Thornwood.",
                    "category": "history",
                    "confidence": "stated",
                    "object_entities": ["thornwood"],
                    "source_session": 5,
                }
            ],
            "referenced_by": [],
        }
        (session_005_dir / "baron-aldric.json").write_text(
            json.dumps(session_005_facts)
        )

        session_010_facts = {
            "entity_id": "baron-aldric",
            "facts": [
                {
                    "text": "Baron Aldric cast a spell.",
                    "category": "abilities",
                    "confidence": "observed",
                    "object_entities": [],
                    "source_session": 10,
                }
            ],
            "referenced_by": [],
        }
        (session_010_dir / "baron-aldric.json").write_text(
            json.dumps(session_010_facts)
        )

        # Create target file path
        data_dir = tmp_path / "entities" / "data"
        data_dir.mkdir(parents=True)
        target_file = data_dir / "baron-aldric.json"

        # Create mock SCons nodes
        source_node_1 = MagicMock()
        source_node_1.__str__ = MagicMock(
            return_value=str(session_005_dir / "baron-aldric.json")
        )
        source_node_2 = MagicMock()
        source_node_2.__str__ = MagicMock(
            return_value=str(session_010_dir / "baron-aldric.json")
        )
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action
        result = merge_action([target_node], [source_node_1, source_node_2], env=None)

        assert result == 0
        assert target_file.exists()

        # Verify merged data
        merged_data = json.loads(target_file.read_text())
        assert merged_data["entity_id"] == "baron-aldric"
        assert merged_data["canonical_name"] == "Baron Aldric"
        assert merged_data["aliases"] == ["the Baron"]
        assert merged_data["type"] == "person"
        assert merged_data["first_appearance"] == 3
        assert len(merged_data["facts"]) == 2
        assert merged_data["sessions_appeared"] == [5, 10]

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_raises_entity_not_found_error(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """merge_action raises EntityNotFoundError when entity not in registry."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create empty registry
        registry_data = {"entities": {}}
        registry_file = tmp_path / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create session entity facts file
        session_dir = tmp_path / "entities" / "sessions" / "session-005"
        session_dir.mkdir(parents=True)
        session_facts = {
            "entity_id": "unknown-entity",
            "facts": [],
            "referenced_by": [],
        }
        (session_dir / "unknown-entity.json").write_text(json.dumps(session_facts))

        # Create target file path
        target_file = tmp_path / "entities" / "data" / "unknown-entity.json"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(
            return_value=str(session_dir / "unknown-entity.json")
        )
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action and expect error
        with pytest.raises(EntityNotFoundError) as exc_info:
            merge_action([target_node], [source_node], env=None)

        assert exc_info.value.entity_id == "unknown-entity"

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_raises_entity_mismatch_error(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """merge_action raises EntityMismatchError when session facts have wrong entity_id."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create registry with the target entity
        registry_data = {
            "entities": {
                "baron-aldric": {
                    "canonical_name": "Baron Aldric",
                    "aliases": [],
                    "type": "person",
                    "first_appearance": 3,
                    "description": None,
                }
            }
        }
        registry_file = tmp_path / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create session entity facts file with WRONG entity_id
        session_dir = tmp_path / "entities" / "sessions" / "session-005"
        session_dir.mkdir(parents=True)
        session_facts = {
            "entity_id": "thornwood",  # Wrong entity!
            "facts": [],
            "referenced_by": [],
        }
        # File is named baron-aldric.json but contains thornwood data
        (session_dir / "baron-aldric.json").write_text(json.dumps(session_facts))

        # Create target file path
        target_file = tmp_path / "entities" / "data" / "baron-aldric.json"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(
            return_value=str(session_dir / "baron-aldric.json")
        )
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(target_file))

        # Run action and expect error
        with pytest.raises(EntityMismatchError) as exc_info:
            merge_action([target_node], [source_node], env=None)

        assert exc_info.value.expected == "baron-aldric"
        assert exc_info.value.actual == "thornwood"


class TestRegisterAction:
    """Tests for register_action SCons action."""

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_adds_new_entities_to_registry(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """register_action adds new entities from extraction to registry."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create empty registry
        registry_data = {"entities": {}}
        registry_file = tmp_path / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create extraction file with new entity
        extracted_dir = tmp_path / "sessions" / "extracted"
        extracted_dir.mkdir(parents=True)
        extraction_data = {
            "session_number": 5,
            "extracted_at": "2024-01-01T00:00:00Z",
            "registry_commit": "abc123",
            "extractor_version": "1.0.0",
            "context_resolutions": [],
            "entities": [
                {
                    "entity_id": "baron-aldric",
                    "canonical_name": "Baron Aldric",
                    "aliases": ["the Baron"],
                    "type": "person",
                    "first_appearance": 5,
                }
            ],
            "facts": [],
        }
        extraction_file = extracted_dir / "session-005.json"
        extraction_file.write_text(json.dumps(extraction_data))

        # Create marker file path
        marker_dir = tmp_path / "entities" / "sessions" / "session-005"
        marker_file = marker_dir / ".register_complete"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(extraction_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(marker_file))

        # Run action
        result = register_action([target_node], [source_node], env=None)

        assert result == 0
        assert marker_file.exists()

        # Verify registry was updated
        updated_registry = json.loads(registry_file.read_text())
        assert "baron-aldric" in updated_registry["entities"]
        assert (
            updated_registry["entities"]["baron-aldric"]["canonical_name"]
            == "Baron Aldric"
        )

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_merges_existing_entity(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """register_action merges with existing entity in registry."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create registry with existing entity
        registry_data = {
            "entities": {
                "baron-aldric": {
                    "canonical_name": "Baron Aldric",
                    "aliases": ["the Baron"],
                    "type": "person",
                    "first_appearance": 3,
                    "description": None,
                }
            }
        }
        registry_file = tmp_path / "entity-registry.json"
        registry_file.write_text(json.dumps(registry_data))

        # Create extraction file with same entity, new alias
        extracted_dir = tmp_path / "sessions" / "extracted"
        extracted_dir.mkdir(parents=True)
        extraction_data = {
            "session_number": 10,
            "extracted_at": "2024-01-01T00:00:00Z",
            "registry_commit": "abc123",
            "extractor_version": "1.0.0",
            "context_resolutions": [],
            "entities": [
                {
                    "entity_id": "baron-aldric",
                    "canonical_name": "Baron Aldric",
                    "aliases": ["Lord Aldric"],
                    "type": "person",
                    "first_appearance": 10,
                }
            ],
            "facts": [],
        }
        extraction_file = extracted_dir / "session-010.json"
        extraction_file.write_text(json.dumps(extraction_data))

        # Create marker file path
        marker_dir = tmp_path / "entities" / "sessions" / "session-010"
        marker_file = marker_dir / ".register_complete"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(extraction_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(marker_file))

        # Run action
        result = register_action([target_node], [source_node], env=None)

        assert result == 0

        # Verify registry was merged (aliases combined, min first_appearance)
        updated_registry = json.loads(registry_file.read_text())
        entity = updated_registry["entities"]["baron-aldric"]
        assert "the Baron" in entity["aliases"]
        assert "Lord Aldric" in entity["aliases"]
        assert entity["first_appearance"] == 3  # min of 3 and 10

    @patch("wikify.builders.aggregation.get_data_repo_path")
    def test_no_entities_does_not_modify_registry(
        self, mock_get_data_repo_path: MagicMock, tmp_path: Path
    ) -> None:
        """register_action with no entities leaves registry unchanged."""
        mock_get_data_repo_path.return_value = tmp_path

        # Create registry
        registry_data = {
            "entities": {
                "existing": {
                    "canonical_name": "Existing",
                    "aliases": [],
                    "type": "thing",
                    "first_appearance": 1,
                    "description": None,
                }
            }
        }
        registry_file = tmp_path / "entity-registry.json"
        original_content = json.dumps(registry_data)
        registry_file.write_text(original_content)

        # Create extraction file with no entities
        extracted_dir = tmp_path / "sessions" / "extracted"
        extracted_dir.mkdir(parents=True)
        extraction_data = {
            "session_number": 5,
            "extracted_at": "2024-01-01T00:00:00Z",
            "registry_commit": "abc123",
            "extractor_version": "1.0.0",
            "context_resolutions": [],
            "entities": [],
            "facts": [],
        }
        extraction_file = extracted_dir / "session-005.json"
        extraction_file.write_text(json.dumps(extraction_data))

        # Create marker file path
        marker_dir = tmp_path / "entities" / "sessions" / "session-005"
        marker_file = marker_dir / ".register_complete"

        # Create mock SCons nodes
        source_node = MagicMock()
        source_node.__str__ = MagicMock(return_value=str(extraction_file))
        target_node = MagicMock()
        target_node.__str__ = MagicMock(return_value=str(marker_file))

        # Run action
        result = register_action([target_node], [source_node], env=None)

        assert result == 0

        # Verify registry content unchanged
        assert registry_file.read_text() == original_content
