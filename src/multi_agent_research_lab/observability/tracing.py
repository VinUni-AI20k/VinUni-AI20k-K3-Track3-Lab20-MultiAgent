"""Tracing hooks and portable local trace export."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.state import ResearchState


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Record a minimal local span."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started


@contextmanager
def langsmith_trace_context(settings: Settings) -> Iterator[None]:
    """Enable LangSmith only when its API key is configured."""

    if not settings.langsmith_api_key:
        yield
        return

    from langsmith import Client, tracing_context

    if settings.langsmith_endpoint:
        client = Client(
            api_key=settings.langsmith_api_key,
            api_url=settings.langsmith_endpoint,
        )
    else:
        client = Client(api_key=settings.langsmith_api_key)

    try:
        with tracing_context(
            client=client,
            project_name=settings.langsmith_project,
            enabled=True,
        ):
            yield
    finally:
        client.flush()


def export_state_trace(state: ResearchState, destination: Path) -> Path:
    """Write a portable local trace artifact as UTF-8 JSON."""

    payload = {
        "request": state.request.model_dump(),
        "route_history": state.route_history,
        "iteration": state.iteration,
        "input_tokens": state.input_tokens,
        "output_tokens": state.output_tokens,
        "estimated_cost_usd": state.estimated_cost_usd,
        "errors": state.errors,
        "trace": state.trace,
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination
