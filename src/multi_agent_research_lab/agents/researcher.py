"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Collect de-duplicated sources and citation-ready notes."""

        sources = self.search_client.search(state.request.query, state.request.max_sources)
        unique = {
            source.url or source.title: source for source in sources if source.snippet.strip()
        }
        state.sources = list(unique.values())[: state.request.max_sources]
        state.research_notes = "\n".join(
            f"[{index}] {source.title}: {source.snippet}"
            for index, source in enumerate(state.sources, start=1)
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes or "No sources found.",
                metadata={"source_count": len(state.sources)},
            )
        )
        return state
