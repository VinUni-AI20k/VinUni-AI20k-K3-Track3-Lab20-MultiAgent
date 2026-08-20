"""Bounded multi-agent workflow with an optional LangGraph-compatible shape."""

from time import perf_counter

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.supervisor = SupervisorAgent(self.settings)
        self.agents = {
            "researcher": ResearcherAgent(),
            "analyst": AnalystAgent(),
            "writer": WriterAgent(),
        }

    def build(self) -> dict[str, object]:
        """Return the explicit node/edge definition used by the runner."""

        return {
            "nodes": {"supervisor": self.supervisor, **self.agents},
            "edges": {
                "supervisor": ["researcher", "analyst", "writer", "done"],
                "researcher": ["supervisor"],
                "analyst": ["supervisor"],
                "writer": ["supervisor"],
            },
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute nodes with timeout, bounded retries, tracing, and writer fallback."""

        started = perf_counter()
        while state.iteration <= self.settings.max_iterations:
            if perf_counter() - started > self.settings.timeout_seconds:
                state.errors.append("Workflow timeout exceeded")
                break
            self.supervisor.run(state)
            route = state.route_history[-1]
            if route == "done":
                break
            agent = self.agents[route]
            last_error: Exception | None = None
            for attempt in range(1, 3):
                try:
                    with trace_span(route, {"attempt": attempt}) as span:
                        agent.run(state)
                    state.add_trace_event("agent", span)
                    last_error = None
                    break
                except Exception as exc:  # boundary: provider/network errors become state
                    last_error = exc
                    state.errors.append(f"{route} attempt {attempt}: {exc}")
            if last_error is not None:
                if route != "writer" and (state.research_notes or state.analysis_notes):
                    self.agents["writer"].run(state)
                break

        if not state.final_answer:
            detail = "; ".join(state.errors) or "no route produced an answer"
            raise AgentExecutionError(f"Workflow failed: {detail}")
        return state
