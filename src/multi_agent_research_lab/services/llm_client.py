"""LLM client abstraction backed by the OpenAI Responses API."""

from dataclasses import dataclass
from typing import Any

from langsmith.wrappers import wrap_openai
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider wrapper used by agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()

        if client is not None:
            self._client: Any | None = client
        elif self.settings.openai_api_key:
            raw_client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=float(self.settings.timeout_seconds),
                max_retries=0,
            )
            self._client = (
                wrap_openai(raw_client) if self.settings.langsmith_api_key else raw_client
            )
        else:
            self._client = None

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=stop_after_attempt(2),
        reraise=True,
    )
    def _create_response(self, system_prompt: str, user_prompt: str) -> Any:
        if self._client is None:
            raise AgentExecutionError(
                "OPENAI_API_KEY is missing. Add it to .env before calling the LLM."
            )

        return self._client.responses.create(
            model=self.settings.openai_model,
            instructions=system_prompt,
            input=user_prompt,
            store=False,
        )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return text and provider-reported token usage."""

        try:
            response = self._create_response(system_prompt, user_prompt)
        except AgentExecutionError:
            raise
        except (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        ) as exc:
            raise AgentExecutionError(f"OpenAI request failed after retry: {exc}") from exc

        content = getattr(response, "output_text", "")
        if not isinstance(content, str) or not content.strip():
            raise AgentExecutionError("OpenAI returned an empty text response.")

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)

        return LLMResponse(
            content=content.strip(),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(
        self,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> float | None:
        input_rate = self.settings.openai_input_cost_per_1m_tokens
        output_rate = self.settings.openai_output_cost_per_1m_tokens

        if (
            input_tokens is None
            or output_tokens is None
            or input_rate is None
            or output_rate is None
        ):
            return None

        return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
