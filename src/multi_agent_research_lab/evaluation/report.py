"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown.

    TODO(student): Add richer analysis, examples, screenshots, and trace links.
    """

    lines = [
        "# Benchmark Report",
        "",
        "> Cost is an estimate from OpenAI input/output token rates only; it excludes "
        "Tavily fees and does not separate cached input tokens.",
        "",
        "| Query | Run | Latency (s) | Cost (USD) | Quality | Citation cov. | "
        "Failure rate | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation = "" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        query = item.query.replace("|", "\\|")
        lines.append(
            f"| {query} | {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} "
            f"| {citation} | {failure} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## Methodology notes",
            "",
            "- Cost is an estimate from OpenAI text-token prices only.",
            "- Tavily fees and cached-input discounts are excluded.",
            "- Quality score must be assigned manually using the peer-review rubric.",
        ]
    )
    return "\n".join(lines) + "\n"
