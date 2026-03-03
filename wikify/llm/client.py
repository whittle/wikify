"""LLM client abstraction for the pipeline."""

import logging
import tempfile
from typing import Protocol

import anthropic
from anthropic.types import TextBlock
from wikify.config import Config, global_config

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM clients."""

    def complete(self, prompt: str) -> str:
        """Generate a completion for the given prompt."""
        ...


class AnthropicClient:
    """Anthropic Claude client implementation."""

    def __init__(
        self,
        config: Config = global_config,
    ) -> None:
        self.config = config
        self.client = anthropic.Anthropic()

    def complete(self, prompt: str) -> str:
        """Generate a completion using Claude."""
        if self.config.llm_file_logging:
            with tempfile.NamedTemporaryFile(
                mode="w",
                prefix="llm_prompt_",
                suffix=".txt",
                delete=False,
            ) as f:
                f.write(prompt)
                logger.info(f"LLM prompt saved to: {f.name}")

        message = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract text from the response
        content = message.content[0]
        if isinstance(content, TextBlock):
            response = content.text
        else:
            raise ValueError(f"Unexpected content type: {type(content)}")

        if self.config.llm_file_logging:
            with tempfile.NamedTemporaryFile(
                mode="w",
                prefix="llm_response_",
                suffix=".txt",
                delete=False,
            ) as f:
                f.write(response)
                logger.info(f"LLM response saved to: {f.name}")

        return response


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
