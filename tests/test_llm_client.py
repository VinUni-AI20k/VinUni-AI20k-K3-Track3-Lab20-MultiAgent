from types import SimpleNamespace

import pytest

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.services.llm_client import LLMClient


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text="A concise model answer.",
            usage=SimpleNamespace(input_tokens=12, output_tokens=8),
        )


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_complete_maps_text_and_usage() -> None:
    fake_client = FakeClient()
    settings = Settings(
        _env_file=None,
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="gpt-4o-mini",
        TIMEOUT_SECONDS=5,
    )

    result = LLMClient(settings=settings, client=fake_client).complete(
        system_prompt="You are helpful.",
        user_prompt="Explain multi-agent systems.",
    )

    assert result.content == "A concise model answer."
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    assert result.cost_usd is None
    assert fake_client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_complete_requires_api_key_without_injected_client() -> None:
    settings = Settings(_env_file=None, OPENAI_API_KEY=None)

    with pytest.raises(AgentExecutionError, match="OPENAI_API_KEY"):
        LLMClient(settings=settings).complete(
            system_prompt="You are helpful.",
            user_prompt="Explain multi-agent systems.",
        )


def test_complete_estimates_cost_when_rates_are_configured() -> None:
    fake_client = FakeClient()
    settings = Settings(
        _env_file=None,
        OPENAI_API_KEY="test-key",
        OPENAI_INPUT_COST_PER_1M_TOKENS=1.0,
        OPENAI_OUTPUT_COST_PER_1M_TOKENS=2.0,
    )

    result = LLMClient(settings=settings, client=fake_client).complete(
        system_prompt="You are helpful.",
        user_prompt="Explain multi-agent systems.",
    )

    assert result.cost_usd == pytest.approx(0.000028)
