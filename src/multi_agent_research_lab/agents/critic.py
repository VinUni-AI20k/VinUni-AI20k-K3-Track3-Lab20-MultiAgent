"""Optional critic agent skeleton for bonus work."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.state import ResearchState


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Add lightweight citation and completeness findings to the trace."""

        answer = state.final_answer or ""
        cited = sum(f"[{index}]" in answer for index in range(1, len(state.sources) + 1))
        coverage = cited / len(state.sources) if state.sources else 0.0
        findings = {
            "has_answer": bool(answer.strip()),
            "citation_coverage": coverage,
            "has_references": "References" in answer,
        }
        state.add_trace_event("critic", findings)
        if not findings["has_answer"]:
            state.errors.append("Critic: final answer is empty")
        return state
