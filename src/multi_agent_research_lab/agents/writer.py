"""Writer agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.final_answer with source references."""

        context = state.analysis_notes or state.research_notes
        if not context:
            message = "Analysis notes or research notes are required before writing."
            state.errors.append(f"{self.name}: {message}")
            state.add_trace_event("writer.failed", {"error": message})
            return state

        try:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are a careful technical writer. Answer directly for the target "
                    "audience. Use only the supplied context, state uncertainty clearly, "
                    "and do not invent citations."
                ),
                user_prompt=(
                    f"Audience: {state.request.audience}\n"
                    f"Question: {state.request.query}\n\n"
                    f"Analysis context:\n{context}\n\n"
                    "Write a concise final answer. Do not add a references section; "
                    "the application will append verified source references."
                ),
            )
        except AgentExecutionError as exc:
            state.errors.append(f"{self.name}: {exc}")
            state.add_trace_event("writer.failed", {"error": str(exc)})
            return state

        references = self._format_references(state.sources)
        state.final_answer = (
            f"{response.content}\n\n## Sources\n{references}" if references else response.content
        )
        state.add_usage(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "source_count": len(state.sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        state.add_trace_event("writer.done", {"source_count": len(state.sources)})
        return state

    @staticmethod
    def _format_references(sources: list[SourceDocument]) -> str:
        return "\n".join(
            f"[{index}] {source.title}" + (f" ({source.url})" if source.url else "")
            for index, source in enumerate(sources, start=1)
        )
