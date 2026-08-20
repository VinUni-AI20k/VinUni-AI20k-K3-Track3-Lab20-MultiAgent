"""Analyst agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.analysis_notes."""

        if not state.sources or not state.research_notes:
            message = "Sources and research notes are required before analysis."
            state.errors.append(f"{self.name}: {message}")
            state.add_trace_event("analyst.failed", {"error": message})
            return state

        try:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are an evidence analyst. Extract supported claims, compare "
                    "viewpoints, identify uncertainty, and flag weak evidence. "
                    "Do not add facts that are absent from the supplied context."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n\n"
                    f"Research notes:\n{state.research_notes}\n\n"
                    f"Available sources:\n{self._format_sources(state.sources)}\n\n"
                    "Return: key findings, source reliability observations, "
                    "limitations, and recommended answer framing."
                ),
            )
        except AgentExecutionError as exc:
            state.errors.append(f"{self.name}: {exc}")
            state.add_trace_event("analyst.failed", {"error": str(exc)})
            return state

        state.analysis_notes = response.content
        state.add_usage(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        state.add_trace_event("analyst.done", {"source_count": len(state.sources)})
        return state

    @staticmethod
    def _format_sources(sources: list[SourceDocument]) -> str:
        return "\n".join(
            f"[{index}] {source.title}: {source.snippet}"
            for index, source in enumerate(sources, start=1)
        )
