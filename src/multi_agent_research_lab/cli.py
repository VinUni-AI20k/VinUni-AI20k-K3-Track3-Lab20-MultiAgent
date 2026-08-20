"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.agents import AnalystAgent, ResearcherAgent, WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
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


def _run_baseline(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    ResearcherAgent().run(state)
    AnalystAgent().run(state)
    WriterAgent().run(state)
    return state


def _run_multi_agent(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    return MultiAgentWorkflow().run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-process research baseline."""

    _init()
    request = _parse_query(query)
    state = _run_baseline(request.query)
    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the bounded multi-agent workflow."""

    _init()
    state = ResearchState(request=_parse_query(query))
    workflow = MultiAgentWorkflow()
    result = workflow.run(state)
    LocalArtifactStore().write_text("latest_trace.json", result.model_dump_json(indent=2))
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Benchmark query")] = (
        "Compare single-agent and multi-agent workflows for customer support"
    ),
) -> None:
    """Benchmark both workflows and write the required Markdown report."""

    _init()
    _parse_query(query)
    _, baseline_metrics = run_benchmark("single-agent baseline", query, _run_baseline)
    multi_state, multi_metrics = run_benchmark("supervisor multi-agent", query, _run_multi_agent)
    report = render_markdown_report([baseline_metrics, multi_metrics])
    store = LocalArtifactStore()
    report_path = store.write_text("benchmark_report.md", report)
    store.write_text("benchmark_trace.json", multi_state.model_dump_json(indent=2))
    console.print(Panel.fit(report, title=f"Saved: {report_path}"))


if __name__ == "__main__":
    app()
