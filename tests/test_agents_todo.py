from time import perf_counter

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


def make_supervisor(max_iterations: int = 6) -> SupervisorAgent:
    settings = Settings(
        _env_file=None,
        MAX_ITERATIONS=max_iterations,
        TIMEOUT_SECONDS=5,
    )
    return SupervisorAgent(settings=settings)


def state_with_research() -> ResearchState:
    return ResearchState(
        request=ResearchQuery(query="Explain multi-agent systems"),
        sources=[
            SourceDocument(
                title="Source A",
                url="https://example.com/a",
                snippet="Evidence for the answer.",
            )
        ],
        research_notes="Research notes from Source A.",
    )


def test_supervisor_routes_happy_path() -> None:
    supervisor = make_supervisor()
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))

    supervisor.run(state)
    assert state.next_route == "researcher"

    state.sources = [
        SourceDocument(
            title="Source A",
            url="https://example.com/a",
            snippet="Evidence for the answer.",
        )
    ]
    state.research_notes = "Research notes from Source A."
    supervisor.run(state)
    assert state.next_route == "analyst"

    state.analysis_notes = "Analysis notes."
    supervisor.run(state)
    assert state.next_route == "writer"

    state.final_answer = "Final answer."
    supervisor.run(state)
    assert state.next_route == "done"
    assert state.route_history == ["researcher", "analyst", "writer"]


def test_supervisor_stops_at_max_iterations() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.iteration = 1

    make_supervisor(max_iterations=1).run(state)

    assert state.next_route == "done"
    assert "max iterations" in state.errors[-1]


def test_supervisor_stops_after_timeout() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.started_at = perf_counter() - 10

    make_supervisor().run(state)

    assert state.next_route == "done"
    assert "timeout" in state.errors[-1]


def test_supervisor_retries_analyst_once_then_falls_back_to_writer() -> None:
    state = state_with_research()
    state.errors.append("analyst: invalid analysis output")
    supervisor = make_supervisor()

    supervisor.run(state)
    assert state.next_route == "analyst"
    assert state.retry_counts["analyst"] == 1

    supervisor.run(state)
    assert state.next_route == "writer"
