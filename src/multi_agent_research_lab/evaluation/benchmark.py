"""Benchmark helpers for single-agent versus multi-agent runs."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def compute_citation_coverage(state: ResearchState) -> float:
    """Return the fraction of sources cited by title or URL in the final answer."""

    if not state.sources or not state.final_answer:
        return 0.0

    answer = state.final_answer
    cited_sources = 0

    for index, source in enumerate(state.sources, start=1):
        marker = f"[{index}]"
        has_reference = source.title in answer or (source.url is not None and source.url in answer)
        if marker in answer and has_reference:
            cited_sources += 1

    return cited_sources / len(state.sources)


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run one approach and capture its measurable outcome."""

    started = perf_counter()

    try:
        state = runner(query)
    except Exception as exc:
        state = ResearchState(request=ResearchQuery(query=query))
        state.errors.append(f"benchmark: {type(exc).__name__}: {exc}")

    latency = perf_counter() - started
    failed = bool(state.errors) or not state.final_answer

    metrics = BenchmarkMetrics(
        run_name=run_name,
        query=query,
        latency_seconds=latency,
        estimated_cost_usd=(state.estimated_cost_usd if state.priced_call_count > 0 else None),
        citation_coverage=compute_citation_coverage(state),
        failure_rate=1.0 if failed else 0.0,
        notes="; ".join(state.errors),
    )
    return state, metrics
