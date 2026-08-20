from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


class FakeResearcher:
    def run(self, state: ResearchState) -> ResearchState:
        state.sources = [
            SourceDocument(
                title="Source A",
                url="https://example.com/a",
                snippet="Evidence.",
            )
        ]
        state.research_notes = "Research notes."
        return state


class FakeAnalyst:
    def run(self, state: ResearchState) -> ResearchState:
        state.analysis_notes = "Analysis notes."
        return state


class FakeWriter:
    def run(self, state: ResearchState) -> ResearchState:
        state.final_answer = "Final answer."
        return state


def test_workflow_runs_happy_path() -> None:
    settings = Settings(_env_file=None, MAX_ITERATIONS=6, TIMEOUT_SECONDS=5)
    workflow = MultiAgentWorkflow(
        settings=settings,
        supervisor=SupervisorAgent(settings=settings),
        researcher=FakeResearcher(),  # type: ignore[arg-type]
        analyst=FakeAnalyst(),  # type: ignore[arg-type]
        writer=FakeWriter(),  # type: ignore[arg-type]
    )

    result = workflow.run(ResearchState(request=ResearchQuery(query="Explain multi-agent systems")))

    assert result.final_answer == "Final answer."
    assert result.route_history == ["researcher", "analyst", "writer"]
    assert result.next_route == "done"


def test_workflow_stops_when_max_iterations_is_reached() -> None:
    settings = Settings(_env_file=None, MAX_ITERATIONS=1, TIMEOUT_SECONDS=5)
    workflow = MultiAgentWorkflow(
        settings=settings,
        supervisor=SupervisorAgent(settings=settings),
        researcher=FakeResearcher(),  # type: ignore[arg-type]
        analyst=FakeAnalyst(),  # type: ignore[arg-type]
        writer=FakeWriter(),  # type: ignore[arg-type]
    )

    result = workflow.run(ResearchState(request=ResearchQuery(query="Explain multi-agent systems")))

    assert result.next_route == "done"
    assert result.final_answer is None
    assert any("max iterations" in error for error in result.errors)
