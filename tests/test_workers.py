from multi_agent_research_lab.agents import AnalystAgent, ResearcherAgent, WriterAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMResponse


class FakeLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(
            content="Fake worker output.",
            input_tokens=10,
            output_tokens=5,
        )


class FakeSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        return [
            SourceDocument(
                title="Source A",
                url="https://example.com/a",
                snippet="Evidence for the answer.",
            )
        ]


class FailingSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        raise AgentExecutionError("search unavailable")


def make_state() -> ResearchState:
    return ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))


def test_researcher_success_records_sources_usage_and_trace() -> None:
    state = make_state()
    ResearcherAgent(
        search_client=FakeSearchClient(),  # type: ignore[arg-type]
        llm_client=FakeLLMClient(),  # type: ignore[arg-type]
    ).run(state)

    assert len(state.sources) == 1
    assert state.research_notes == "Fake worker output."
    assert state.input_tokens == 10
    assert state.output_tokens == 5
    assert state.trace[-1]["name"] == "researcher.done"


def test_researcher_search_error_is_prefixed() -> None:
    state = make_state()
    ResearcherAgent(
        search_client=FailingSearchClient(),  # type: ignore[arg-type]
        llm_client=FakeLLMClient(),  # type: ignore[arg-type]
    ).run(state)

    assert state.errors[-1] == "researcher: search unavailable"


def test_analyst_missing_context_does_not_call_llm() -> None:
    state = make_state()
    AnalystAgent(llm_client=FakeLLMClient()).run(state)  # type: ignore[arg-type]

    assert state.errors[-1].startswith("analyst:")
    assert state.analysis_notes is None
    assert state.input_tokens == 0


def test_analyst_success_creates_analysis_notes() -> None:
    state = make_state()
    state.sources = FakeSearchClient().search(state.request.query)
    state.research_notes = "Research notes."

    AnalystAgent(llm_client=FakeLLMClient()).run(state)  # type: ignore[arg-type]

    assert state.analysis_notes == "Fake worker output."
    assert state.trace[-1]["name"] == "analyst.done"


def test_writer_uses_analysis_and_adds_sources() -> None:
    state = make_state()
    state.sources = FakeSearchClient().search(state.request.query)
    state.research_notes = "Research notes."
    state.analysis_notes = "Analysis notes."

    WriterAgent(llm_client=FakeLLMClient()).run(state)  # type: ignore[arg-type]

    assert state.final_answer is not None
    assert "Fake worker output." in state.final_answer
    assert "## Sources" in state.final_answer
    assert "https://example.com/a" in state.final_answer


def test_writer_missing_context_is_prefixed() -> None:
    state = make_state()
    WriterAgent(llm_client=FakeLLMClient()).run(state)  # type: ignore[arg-type]

    assert state.errors[-1].startswith("writer:")
