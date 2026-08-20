"""Search client abstraction for ResearcherAgent."""

import json
from urllib.request import Request, urlopen

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Tavily search with a small, transparent offline reference set."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search Tavily when configured, otherwise return relevant primary references."""

        if self.settings.tavily_api_key:
            payload = json.dumps(
                {
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                }
            ).encode()
            request = Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:  # noqa: S310
                data = json.load(response)
            return [
                SourceDocument(
                    title=item.get("title", "Untitled"),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    metadata={"provider": "tavily", "score": item.get("score")},
                )
                for item in data.get("results", [])[:max_results]
            ]

        references = [
            SourceDocument(
                title="Building effective agents",
                url="https://www.anthropic.com/engineering/building-effective-agents",
                snippet=(
                    "Use simple composable workflows first; add autonomous agents when flexible "
                    "model-directed decisions are necessary."
                ),
                metadata={"provider": "offline", "publisher": "Anthropic"},
            ),
            SourceDocument(
                title="OpenAI Agents SDK — Orchestrating multiple agents",
                url="https://openai.github.io/openai-agents-python/multi_agent/",
                snippet=(
                    "Manager-style orchestration keeps control in one agent, while "
                    "handoffs transfer "
                    "control to a specialist."
                ),
                metadata={"provider": "offline", "publisher": "OpenAI"},
            ),
            SourceDocument(
                title="LangGraph overview",
                url="https://docs.langchain.com/oss/python/langgraph/overview",
                snippet=(
                    "LangGraph supports durable execution, human-in-the-loop, memory, and stateful "
                    "orchestration for long-running agents."
                ),
                metadata={"provider": "offline", "publisher": "LangChain"},
            ),
            SourceDocument(
                title="GraphRAG: Unlocking LLM discovery on narrative private data",
                url="https://www.microsoft.com/en-us/research/project/graphrag/",
                snippet=(
                    "GraphRAG extracts structured knowledge from unstructured text and uses graph "
                    "summaries to answer global questions over a corpus."
                ),
                metadata={"provider": "offline", "publisher": "Microsoft Research"},
            ),
            SourceDocument(
                title="ReAct: Synergizing Reasoning and Acting in Language Models",
                url="https://arxiv.org/abs/2210.03629",
                snippet=(
                    "Interleaving reasoning traces with actions lets language models update plans "
                    "using observations from external environments."
                ),
                metadata={"provider": "offline", "publisher": "arXiv"},
            ),
        ]
        return references[:max_results]
