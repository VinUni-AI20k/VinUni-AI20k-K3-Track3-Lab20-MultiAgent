"""LangGraph workflow for the multi-agent research system."""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState, RouteName
from multi_agent_research_lab.observability.tracing import langsmith_trace_context


class MultiAgentWorkflow:
    """Builds and runs the Supervisor -> workers graph."""

    def __init__(
        self,
        settings: Settings | None = None,
        supervisor: SupervisorAgent | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.supervisor = supervisor or SupervisorAgent(settings=self.settings)
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()

    def build(self) -> Any:
        """Create and compile the LangGraph workflow."""

        graph = StateGraph(ResearchState)

        graph.add_node("supervisor", self._run_supervisor)
        graph.add_node("researcher", self._run_researcher)
        graph.add_node("analyst", self._run_analyst)
        graph.add_node("writer", self._run_writer)

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_from_state,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return the final shared state."""

        with langsmith_trace_context(self.settings):
            result = self._invoke_graph(state.model_dump())
        return ResearchState.model_validate(result)

    @traceable(name="multi-agent-workflow", run_type="chain")
    def _invoke_graph(self, state_payload: dict[str, Any]) -> dict[str, Any]:
        graph = self.build()
        return cast(
            dict[str, Any],
            graph.invoke(
                state_payload,
                config={"recursion_limit": self.settings.max_iterations * 2 + 2},
            ),
        )

    def _run_supervisor(self, state: ResearchState) -> dict[str, Any]:
        return self.supervisor.run(state).model_dump()

    def _run_researcher(self, state: ResearchState) -> dict[str, Any]:
        return self.researcher.run(state).model_dump()

    def _run_analyst(self, state: ResearchState) -> dict[str, Any]:
        return self.analyst.run(state).model_dump()

    def _run_writer(self, state: ResearchState) -> dict[str, Any]:
        return self.writer.run(state).model_dump()

    @staticmethod
    def _route_from_state(state: ResearchState) -> RouteName:
        return state.next_route or "done"


def run_multi_agent(
    query: str,
    workflow: MultiAgentWorkflow | None = None,
) -> ResearchState:
    """Run the complete workflow for one benchmark query."""

    state = ResearchState(request=ResearchQuery(query=query))
    return (workflow or MultiAgentWorkflow()).run(state)
