from pathlib import Path
from time import perf_counter

from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import export_state_trace


def test_state_records_route_and_trace() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.record_route("researcher")
    state.add_trace_event("route", {"next": "researcher"})
    assert state.iteration == 1
    assert state.route_history == ["researcher"]
    assert state.trace[0]["name"] == "route"


def test_state_tracks_route_usage_retries_and_timeout() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))

    state.set_next_route("researcher")
    state.add_usage(input_tokens=12, output_tokens=8, cost_usd=0.001)
    retry_count = state.increment_retry("researcher")

    assert state.next_route == "researcher"
    assert state.route_history == ["researcher"]
    assert state.iteration == 1
    assert state.input_tokens == 12
    assert state.output_tokens == 8
    assert state.estimated_cost_usd == 0.001
    assert retry_count == 1

    state.started_at = perf_counter() - 2
    assert state.has_timed_out(timeout_seconds=1)


def test_export_state_trace(tmp_path: Path) -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.add_trace_event("test.event", {"status": "ok"})

    output = export_state_trace(state, tmp_path / "trace.json")

    assert output.exists()
    assert '"test.event"' in output.read_text(encoding="utf-8")
