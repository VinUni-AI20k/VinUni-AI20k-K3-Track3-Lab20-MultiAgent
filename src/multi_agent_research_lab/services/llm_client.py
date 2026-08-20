"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """OpenAI client with a deterministic offline fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4), reraise=True)
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a completion and usage; run locally when no API key is configured."""

        if not self.settings.openai_api_key:
            return self._offline_completion(user_prompt)

        try:
            from openai import OpenAI
        except ImportError:
            return self._offline_completion(user_prompt)

        client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=float(self.settings.timeout_seconds),
        )
        response: Any = client.responses.create(
            model=self.settings.openai_model,
            instructions=system_prompt,
            input=user_prompt,
        )
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=response.output_text,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )

    @staticmethod
    def _offline_completion(user_prompt: str) -> LLMResponse:
        words = user_prompt.split()
        excerpt = " ".join(words[:180])
        content = (
            f"Offline synthesis (set OPENAI_API_KEY for a model-generated response):\n\n{excerpt}"
        )
        return LLMResponse(
            content=content, input_tokens=len(words), output_tokens=len(content.split())
        )
