from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_workflow_completes_offline_with_citations() -> None:
    state = ResearchState(request=ResearchQuery(query="Compare multi-agent orchestration patterns"))
    result = MultiAgentWorkflow().run(state)
    assert result.final_answer
    assert "References" in result.final_answer
    assert result.route_history == ["researcher", "analyst", "writer", "done"]
    assert len(result.trace) >= 7
