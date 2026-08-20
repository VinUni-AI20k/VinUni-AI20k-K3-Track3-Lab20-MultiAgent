"""Command-line entrypoint for the multi-agent research lab."""

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError, StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow, run_multi_agent
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import export_state_trace, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _load_benchmark_queries(config_path: Path) -> list[str]:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise typer.BadParameter(f"Cannot read config: {exc}") from exc

    if not isinstance(payload, dict):
        raise typer.BadParameter("Benchmark config must be a YAML object.")

    benchmark = payload.get("benchmark")
    if not isinstance(benchmark, dict):
        raise typer.BadParameter("Missing benchmark section in config.")

    queries = benchmark.get("queries")
    if (
        not isinstance(queries, list)
        or not queries
        or not all(isinstance(query, str) and query.strip() for query in queries)
    ):
        raise typer.BadParameter("benchmark.queries must be a non-empty string list.")

    return queries


def run_baseline(
    query: str,
    llm_client: LLMClient | None = None,
) -> ResearchState:
    """Run exactly one LLM call as the single-agent comparison baseline."""

    state = ResearchState(request=ResearchQuery(query=query))
    client = llm_client or LLMClient()

    system_prompt = (
        "You are a concise and accurate research assistant. "
        "Answer only from your general knowledge. "
        "State uncertainty instead of inventing sources or facts."
    )
    user_prompt = (
        f"Audience: {state.request.audience}\n"
        f"Question: {state.request.query}\n\n"
        "Give a clear, self-contained answer."
    )

    with trace_span(
        "baseline",
        {"model": client.settings.openai_model, "mode": "single_agent"},
    ) as span:
        response = client.complete(system_prompt, user_prompt)

    state.final_answer = response.content
    state.add_usage(
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.cost_usd,
    )
    state.agent_results.append(
        AgentResult(
            agent=AgentName.BASELINE,
            content=response.content,
            metadata={
                "mode": "single_agent",
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
    )
    state.add_trace_event(
        "baseline.done",
        {
            "duration_seconds": span["duration_seconds"],
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    )
    return state


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline."""

    _init()
    try:
        state = run_baseline(query)
    except AgentExecutionError as exc:
        console.print(Panel.fit(str(exc), title="Baseline Error", style="red"))
        raise typer.Exit(code=1) from exc

    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))
    console.print(
        f"Input tokens: {state.input_tokens} | "
        f"Output tokens: {state.output_tokens} | "
        f"Estimated cost: ${state.estimated_cost_usd:.4f}"
    )


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=_parse_query(query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    trace_path = export_state_trace(
        result,
        Path("reports/traces/latest_multi_agent_trace.json"),
    )
    console.print(f"Local trace saved to: {trace_path}")
    console.print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, indent=2))


@app.command()
def benchmark(
    config: Annotated[
        Path,
        typer.Option("--config", help="Path to the benchmark YAML configuration"),
    ] = Path("configs/lab_default.yaml"),
) -> None:
    """Benchmark single-agent baseline against the multi-agent workflow."""

    _init()
    queries = _load_benchmark_queries(config)

    metrics = []
    for query in queries:
        _, baseline_metrics = run_benchmark("baseline", query, run_baseline)
        _, multi_agent_metrics = run_benchmark(
            "multi-agent",
            query,
            run_multi_agent,
        )
        metrics.extend([baseline_metrics, multi_agent_metrics])

    report = render_markdown_report(metrics)
    report_path = LocalArtifactStore().write_text("benchmark_report.md", report)

    console.print(f"Benchmark report saved to: {report_path}")
    console.print(report)


if __name__ == "__main__":
    app()
