"""Benchmark single-agent vs multi-agent execution."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, usage, citation coverage, quality proxy, and failure rate."""

    started = perf_counter()
    try:
        state = runner(query)
        failed = not bool(state.final_answer)
    except Exception:
        state = ResearchState.model_validate({"request": {"query": query}})
        failed = True
    latency = perf_counter() - started
    usages = [result.metadata for result in state.agent_results]
    cost_values = [item["cost_usd"] for item in usages if item.get("cost_usd") is not None]
    citations = sum(
        f"[{index}]" in (state.final_answer or "") for index in range(1, len(state.sources) + 1)
    )
    coverage = citations / len(state.sources) if state.sources else 0.0
    quality = min(
        10.0,
        (3.0 if state.final_answer else 0.0)
        + (2.0 if state.analysis_notes else 0.0)
        + 3.0 * coverage
        + min(2.0, len(state.sources) / 2),
    )
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=sum(cost_values) if cost_values else 0.0,
        quality_score=quality,
        citation_coverage=coverage,
        failure_rate=float(failed),
        notes=f"{len(state.sources)} sources; {len(state.trace)} trace events",
    )
    return state, metrics
