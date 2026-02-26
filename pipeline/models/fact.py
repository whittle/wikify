"""Fact model and confidence levels."""

from enum import Enum

from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    """Confidence level for a fact extracted from session notes."""

    STATED = "stated"  # Explicitly said by narrator/GM
    OBSERVED = "observed"  # Directly witnessed by PCs
    CHARACTER_CLAIM = "character_claim"  # Stated by NPC (may be unreliable)
    IMPLIED = "implied"  # Reasonably inferred from events
    RUMOR = "rumor"  # Secondhand, hearsay
    PLAYER_THEORY = "player_theory"  # Out-of-character speculation
    UNCERTAIN = "uncertain"  # Ambiguous, possibly misunderstood
    SUPERSEDED = "superseded"  # Contradicted by later info


class Fact(BaseModel):
    """A single fact extracted from session notes."""

    subject_entity: str  # Canonical name of primary entity
    object_entities: list[str] = []  # Other entities referenced
    text: str  # The fact itself
    category: str  # history, abilities, geography, etc.
    confidence: ConfidenceLevel
