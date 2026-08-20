"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Synthesize an audience-aware response with numbered references."""

        analysis = state.analysis_notes or state.research_notes or "No evidence available."
        prompt = (
            f"Question: {state.request.query}\nAudience: {state.request.audience}\n\n"
            f"Analysis:\n{analysis}\n\n"
            "Write a concise answer. Preserve [n] citations and state evidence limitations."
        )
        response = self.llm_client.complete(
            "You are a careful research writer. Never invent a source or unsupported fact.", prompt
        )
        references = "\n".join(
            f"[{i}] {source.title} — {source.url or 'local source'}"
            for i, source in enumerate(state.sources, 1)
        )
        state.final_answer = response.content + (
            f"\n\nReferences\n{references}" if references else ""
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        return state
