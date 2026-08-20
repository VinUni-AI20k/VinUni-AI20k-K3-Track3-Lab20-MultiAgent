from multi_agent_research_lab.cli import run_baseline
from multi_agent_research_lab.services.llm_client import LLMResponse


class FakeLLMClient:
    class Settings:
        openai_model = "fake-model"

    settings = Settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        assert "concise and accurate" in system_prompt
        assert "Explain multi-agent systems" in user_prompt
        return LLMResponse(
            content="A fake baseline answer.",
            input_tokens=11,
            output_tokens=7,
        )


def test_run_baseline_uses_one_llm_call_and_records_usage() -> None:
    state = run_baseline(
        "Explain multi-agent systems",
        llm_client=FakeLLMClient(),  # type: ignore[arg-type]
    )

    assert state.final_answer == "A fake baseline answer."
    assert state.input_tokens == 11
    assert state.output_tokens == 7
    assert state.agent_results[0].agent == "baseline"
    assert state.agent_results[0].metadata["mode"] == "single_agent"
    assert state.trace[-1]["name"] == "baseline.done"
