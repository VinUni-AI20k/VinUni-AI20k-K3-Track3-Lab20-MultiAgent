from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_each_missing_stage() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    supervisor = SupervisorAgent()
    supervisor.run(state)
    assert state.route_history[-1] == "researcher"
    state.research_notes = "notes"
    supervisor.run(state)
    assert state.route_history[-1] == "analyst"
    state.analysis_notes = "analysis"
    supervisor.run(state)
    assert state.route_history[-1] == "writer"
