"""Deterministic supervisor and router."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState, RouteName


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Choose the next worker from the current shared state."""

        if state.has_timed_out(self.settings.timeout_seconds):
            state.errors.append("supervisor: workflow timeout reached")
            return self._route(state, "done", "workflow timeout")

        if state.iteration >= self.settings.max_iterations:
            state.errors.append("supervisor: max iterations reached")
            return self._route(state, "done", "max iterations reached")

        if not state.sources or not state.research_notes:
            if self._has_agent_error(state, "researcher"):
                return self._retry_or_stop(
                    state,
                    agent_name="researcher",
                    fallback_route="done",
                )
            return self._route(state, "researcher", "sources or research notes are missing")

        if not state.analysis_notes:
            if self._has_agent_error(state, "analyst"):
                return self._retry_or_stop(
                    state,
                    agent_name="analyst",
                    fallback_route="writer",
                )
            return self._route(state, "analyst", "analysis notes are missing")

        if not state.final_answer:
            if self._has_agent_error(state, "writer"):
                return self._retry_or_stop(
                    state,
                    agent_name="writer",
                    fallback_route="done",
                )
            return self._route(state, "writer", "final answer is missing")

        return self._route(state, "done", "final answer is complete")

    @staticmethod
    def _has_agent_error(state: ResearchState, agent_name: str) -> bool:
        return any(error.startswith(f"{agent_name}:") for error in state.errors)

    def _retry_or_stop(
        self,
        state: ResearchState,
        agent_name: str,
        fallback_route: RouteName,
    ) -> ResearchState:
        retry_count = state.retry_counts.get(agent_name, 0)

        if retry_count < 1:
            new_count = state.increment_retry(agent_name)
            return self._route(
                state,
                agent_name,  # type: ignore[arg-type]
                f"retry {agent_name} after failure, attempt {new_count}",
            )

        return self._route(
            state,
            fallback_route,
            f"{agent_name} failed after retry; using fallback",
        )

    @staticmethod
    def _route(
        state: ResearchState,
        route: RouteName,
        reason: str,
    ) -> ResearchState:
        state.set_next_route(route)
        state.add_trace_event(
            "supervisor.decision",
            {
                "next": route,
                "reason": reason,
                "iteration": state.iteration,
            },
        )
        return state
