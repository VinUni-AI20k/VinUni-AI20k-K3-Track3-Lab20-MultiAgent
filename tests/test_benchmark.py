from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    compute_citation_coverage,
    run_benchmark,
)
from multi_agent_research_lab.evaluation.report import render_markdown_report


def test_citation_coverage_is_complete_when_all_sources_are_referenced() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Explain multi-agent systems"),
        sources=[
            SourceDocument(
                title="Source A",
                url="https://example.com/a",
                snippet="Evidence.",
            )
        ],
        final_answer="Answer with [1] Source A (https://example.com/a).",
    )

    assert compute_citation_coverage(state) == 1.0


def test_run_benchmark_success_has_zero_failure_rate_and_unknown_cost() -> None:
    def runner(query: str) -> ResearchState:
        return ResearchState(
            request=ResearchQuery(query=query),
            final_answer="Successful answer.",
        )

    state, metrics = run_benchmark("baseline", "Explain multi-agent systems", runner)

    assert state.final_answer == "Successful answer."
    assert metrics.query == "Explain multi-agent systems"
    assert metrics.failure_rate == 0.0
    assert metrics.estimated_cost_usd is None


def test_run_benchmark_runner_exception_has_failure_rate_one() -> None:
    def runner(query: str) -> ResearchState:
        raise RuntimeError("provider unavailable")

    _, metrics = run_benchmark("multi-agent", "Explain multi-agent systems", runner)

    assert metrics.failure_rate == 1.0
    assert "provider unavailable" in metrics.notes


def test_report_includes_query_and_run_name() -> None:
    _, metrics = run_benchmark(
        "baseline",
        "Explain | multi-agent systems",
        lambda query: ResearchState(
            request=ResearchQuery(query=query),
            final_answer="Answer",
        ),
    )

    report = render_markdown_report([metrics])

    assert "Explain \\| multi-agent systems" in report
    assert "baseline" in report
