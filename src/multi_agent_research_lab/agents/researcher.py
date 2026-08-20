"""Researcher agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.sources and state.research_notes."""

        try:
            sources = self.search_client.search(
                state.request.query,
                max_results=state.request.max_sources,
            )
            if not sources:
                raise AgentExecutionError("Search returned no usable sources.")

            state.sources = sources
            response = self.llm_client.complete(
                system_prompt=(
                    "You are a research assistant. Summarize the supplied sources only. "
                    "Do not invent facts, URLs, or citations."
                ),
                user_prompt=(
                    f"Research question: {state.request.query}\n\n"
                    f"Sources:\n{self._format_sources(sources)}\n\n"
                    "Write concise research notes: key claims, supporting source indexes, "
                    "and important uncertainty."
                ),
            )
        except AgentExecutionError as exc:
            state.errors.append(f"{self.name}: {exc}")
            state.add_trace_event("researcher.failed", {"error": str(exc)})
            return state

        state.research_notes = response.content
        state.add_usage(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=response.content,
                metadata={
                    "source_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        state.add_trace_event(
            "researcher.done",
            {"source_count": len(sources), "provider": sources[0].metadata.get("provider")},
        )
        return state

    @staticmethod
    def _format_sources(sources: list[SourceDocument]) -> str:
        return "\n\n".join(
            f"[{index}] {source.title}\n"
            f"URL: {source.url or 'unavailable'}\n"
            f"Snippet: {source.snippet}"
            for index, source in enumerate(sources, start=1)
        )
