"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Extract claims and explicitly report evidence limitations."""

        if not state.sources:
            state.analysis_notes = (
                "No reliable sources were collected; answer must disclose this limitation."
            )
        else:
            claims = [
                f"- Claim {i}: {source.snippet} [{i}]" for i, source in enumerate(state.sources, 1)
            ]
            state.analysis_notes = (
                "Evidence-backed claims:\n"
                + "\n".join(claims)
                + "\n\nSynthesis: Prefer the simplest orchestration that meets the task; "
                "use explicit state, bounded execution, traceability, and evaluation. "
                "Evidence is limited to the "
                "listed source excerpts and should be re-checked for time-sensitive decisions."
            )
        state.agent_results.append(
            AgentResult(agent=AgentName.ANALYST, content=state.analysis_notes)
        )
        return state
