"""Tests for session extraction orchestration."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from wikify.extraction.errors import InvalidJSONError, SchemaValidationError
from wikify.extraction.extract import EXTRACTOR_VERSION, extract_session
from wikify.git.errors import DirtyRegistryError
from wikify.llm.client import MockLLMClient
from wikify.models import ExtractionResult


class TestExtractSession:
    """Tests for extract_session function."""

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_returns_extraction_result_with_metadata(
        self, mock_get_sha: MagicMock
    ) -> None:
        """Returns ExtractionResult with correct session_number, registry_commit, etc."""
        mock_get_sha.return_value = "abc123def456"
        mock_response = json.dumps(
            {"context_resolutions": [], "entities": [], "facts": []}
        )
        client = MockLLMClient(responses={"": mock_response})

        result = extract_session(
            prompt="Extract facts from: The party entered the dungeon.",
            session_number=7,
            client=client,
        )

        assert isinstance(result, ExtractionResult)
        assert result.session_number == 7
        assert result.registry_commit == "abc123def456"
        assert result.extractor_version == EXTRACTOR_VERSION
        assert isinstance(result.extracted_at, datetime)

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_raises_dirty_registry_error(self, mock_get_sha: MagicMock) -> None:
        """Propagates DirtyRegistryError from git module."""
        mock_get_sha.side_effect = DirtyRegistryError(
            "entity-registry.json has uncommitted changes"
        )
        client = MockLLMClient()

        with pytest.raises(DirtyRegistryError):
            extract_session(
                prompt="Extract facts from: The party entered the dungeon.",
                session_number=7,
                client=client,
            )

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_propagates_invalid_json_error(self, mock_get_sha: MagicMock) -> None:
        """InvalidJSONError from parser flows through."""
        mock_get_sha.return_value = "abc123"
        client = MockLLMClient(responses={"": "not valid json"})

        with pytest.raises(InvalidJSONError):
            extract_session(
                prompt="Extract facts from: The party entered the dungeon.",
                session_number=7,
                client=client,
            )

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_propagates_schema_validation_error(self, mock_get_sha: MagicMock) -> None:
        """SchemaValidationError from parser flows through."""
        mock_get_sha.return_value = "abc123"
        # Missing required fields in fact
        mock_response = json.dumps({"facts": [{"subject_entity": "Baron"}]})
        client = MockLLMClient(responses={"": mock_response})

        with pytest.raises(SchemaValidationError):
            extract_session(
                prompt="Extract facts from: The party entered the dungeon.",
                session_number=7,
                client=client,
            )

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_sets_first_appearance_on_new_entities(
        self, mock_get_sha: MagicMock
    ) -> None:
        """New entities get first_appearance set to session_number."""
        mock_get_sha.return_value = "abc123"
        mock_response = json.dumps(
            {
                "context_resolutions": [],
                "entities": [
                    {
                        "entity_id": "sera-ranger",
                        "canonical_name": "Sera",
                        "aliases": ["the ranger"],
                        "type": "person",
                    },
                    {
                        "entity_id": "mount-tambora",
                        "canonical_name": "Mount Tambora",
                        "aliases": [],
                        "type": "location",
                    },
                ],
                "facts": [],
            }
        )
        client = MockLLMClient(responses={"": mock_response})

        result = extract_session(
            prompt="Extract facts from: Sera guided the party to Mount Tambora.",
            session_number=5,
            client=client,
        )

        assert len(result.entities) == 2
        for entity in result.entities:
            assert entity.first_appearance == 5

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_extracts_facts_correctly(self, mock_get_sha: MagicMock) -> None:
        """Facts are extracted and included in result."""
        mock_get_sha.return_value = "abc123"
        mock_response = json.dumps(
            {
                "context_resolutions": [
                    {"reference": "the Baron", "resolved_to": "Baron Aldric"}
                ],
                "entities": [],
                "facts": [
                    {
                        "subject_entity": "Baron Aldric",
                        "object_entities": ["Thornwood Keep"],
                        "text": "Baron Aldric rules Thornwood Keep.",
                        "category": "governance",
                        "confidence": "stated",
                    }
                ],
            }
        )
        client = MockLLMClient(responses={"": mock_response})

        result = extract_session(
            prompt="Extract facts from: The Baron welcomed us to his keep.",
            session_number=3,
            client=client,
        )

        assert len(result.facts) == 1
        assert result.facts[0].subject_entity == "Baron Aldric"
        assert result.facts[0].text == "Baron Aldric rules Thornwood Keep."

        assert len(result.context_resolutions) == 1
        assert result.context_resolutions[0].reference == "the Baron"

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_extracted_at_is_utc(self, mock_get_sha: MagicMock) -> None:
        """extracted_at timestamp is in UTC."""
        mock_get_sha.return_value = "abc123"
        mock_response = json.dumps(
            {"context_resolutions": [], "entities": [], "facts": []}
        )
        client = MockLLMClient(responses={"": mock_response})

        before = datetime.now(timezone.utc)
        result = extract_session(
            prompt="Extract facts from: Test session.",
            session_number=1,
            client=client,
        )
        after = datetime.now(timezone.utc)

        assert result.extracted_at.tzinfo is not None
        assert before <= result.extracted_at <= after

    @patch("wikify.extraction.extract.get_data_repo_commit_sha")
    def test_passes_prompt_to_llm_unchanged(self, mock_get_sha: MagicMock) -> None:
        """LLM is called with the exact prompt that was passed in."""
        mock_get_sha.return_value = "abc123"
        mock_response = json.dumps(
            {"context_resolutions": [], "entities": [], "facts": []}
        )
        client = MockLLMClient(responses={"": mock_response})
        prompt = "This is a complete prompt with context and session text."

        extract_session(
            prompt=prompt,
            session_number=1,
            client=client,
        )

        assert len(client.calls) == 1
        assert client.calls[0] == prompt
