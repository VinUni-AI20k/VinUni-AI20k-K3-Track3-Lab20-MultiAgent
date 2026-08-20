"""Shared state passed through the multi-agent workflow."""

from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from multi_agent_research_lab.core.schemas import AgentResult, ResearchQuery, SourceDocument

RouteName = Literal["researcher", "analyst", "writer", "done"]


class ResearchState(BaseModel):
    """Single source of truth passed through the workflow."""

    request: ResearchQuery
    iteration: int = 0
    next_route: RouteName | None = None
    route_history: list[str] = Field(default_factory=list)

    sources: list[SourceDocument] = Field(default_factory=list)
    research_notes: str | None = None
    analysis_notes: str | None = None
    final_answer: str | None = None

    agent_results: list[AgentResult] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    priced_call_count: int = 0
    retry_counts: dict[str, int] = Field(default_factory=dict)
    started_at: float = Field(default_factory=perf_counter)

    def record_route(self, route: str) -> None:
        self.route_history.append(route)
        self.iteration += 1

    def set_next_route(self, route: RouteName) -> None:
        """Store the router decision and count a selected worker."""
        self.next_route = route
        if route != "done":
            self.record_route(route)
        self.add_trace_event("supervisor.route", {"next": route})

    def add_trace_event(self, name: str, payload: dict[str, Any]) -> None:
        self.trace.append(
            {
                "name": name,
                "payload": payload,
                "elapsed_seconds": perf_counter() - self.started_at,
            }
        )

    def add_usage(
        self,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0
        if cost_usd is not None:
            self.estimated_cost_usd += cost_usd
            self.priced_call_count += 1

    def increment_retry(self, scope: str) -> int:
        self.retry_counts[scope] = self.retry_counts.get(scope, 0) + 1
        return self.retry_counts[scope]

    def has_timed_out(self, timeout_seconds: float) -> bool:
        return perf_counter() - self.started_at >= timeout_seconds
