"""Tests for extraction builder."""

import pytest

from wikify.builders.extraction import parse_session_number


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
