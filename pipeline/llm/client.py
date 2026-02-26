"""LLM client abstraction for the pipeline."""

from typing import Protocol

import anthropic


class LLMClient(Protocol):
    """Protocol for LLM clients."""

    def complete(self, prompt: str) -> str:
        """Generate a completion for the given prompt."""
        ...


class AnthropicClient:
    """Anthropic Claude client implementation."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
    ) -> None:
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        """Generate a completion using Claude."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract text from the response
        content = message.content[0]
        if hasattr(content, "text"):
            return content.text
        raise ValueError(f"Unexpected content type: {type(content)}")


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        """Return a canned response based on prompt content."""
        self.calls.append(prompt)

        # Check for exact match first
        if prompt in self.responses:
            return self.responses[prompt]

        # Check for partial matches
        for key, response in self.responses.items():
            if key in prompt:
                return response

        # Default response
        return '{"facts": [], "entities": []}'
