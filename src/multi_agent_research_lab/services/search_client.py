"""Search client abstraction for ResearcherAgent."""

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import SourceDocument

SearchTransport = Callable[[str, int], list[SourceDocument]]


def _is_retryable_search_error(error: BaseException) -> bool:
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, HTTPError):
        return error.code == 429 or error.code >= 500
    return isinstance(error, URLError)


class SearchClient:
    """Search through Tavily or deterministic mock results."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: SearchTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Return valid, de-duplicated sources for a query."""

        if not query.strip():
            raise AgentExecutionError("Search query must not be empty.")
        if max_results < 1:
            raise AgentExecutionError("max_results must be at least 1.")

        if self._transport is not None:
            documents = self._transport(query, max_results)
        elif self.settings.tavily_api_key:
            documents = self._search_tavily(query, max_results)
        else:
            documents = self._mock_search(query, max_results)

        return self._normalise(documents, max_results)

    @retry(
        retry=retry_if_exception(_is_retryable_search_error),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=stop_after_attempt(2),
        reraise=True,
    )
    def _fetch_tavily_payload(self, query: str, max_results: int) -> object:
        if not self.settings.tavily_api_key:
            raise AgentExecutionError("TAVILY_API_KEY is missing.")

        body = json.dumps(
            {
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            }
        ).encode("utf-8")

        request = Request(
            "https://api.tavily.com/search",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=self.settings.timeout_seconds) as response:
            return json.load(response)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        try:
            payload = self._fetch_tavily_payload(query, max_results)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentExecutionError(f"Tavily search failed: {type(exc).__name__}") from exc

        if not isinstance(payload, dict):
            raise AgentExecutionError("Tavily returned an invalid response payload.")

        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise AgentExecutionError("Tavily response does not contain a results list.")

        documents: list[SourceDocument] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            url = item.get("url")
            snippet = item.get("content")

            if not isinstance(title, str) or not isinstance(snippet, str):
                continue
            if url is not None and not isinstance(url, str):
                continue

            metadata: dict[str, Any] = {"provider": "tavily"}
            score = item.get("score")
            if isinstance(score, int | float):
                metadata["score"] = score

            documents.append(
                SourceDocument(
                    title=title,
                    url=url,
                    snippet=snippet,
                    metadata=metadata,
                )
            )

        return documents

    @staticmethod
    def _mock_search(query: str, max_results: int) -> list[SourceDocument]:
        """Return clearly-labelled sources for tests or offline demos only."""

        return [
            SourceDocument(
                title=f"Mock research source {index} for: {query}",
                url=f"https://example.invalid/mock-source-{index}",
                snippet=(
                    "This is deterministic mock data for local testing. "
                    "It must not be presented as a real web source."
                ),
                metadata={"provider": "mock", "is_mock": True},
            )
            for index in range(1, max_results + 1)
        ]

    @staticmethod
    def _normalise(
        documents: list[SourceDocument],
        max_results: int,
    ) -> list[SourceDocument]:
        normalised: list[SourceDocument] = []
        seen: set[str] = set()

        for document in documents:
            title = document.title.strip()
            snippet = document.snippet.strip()
            if not title or not snippet:
                continue

            dedup_key = (document.url or title).strip().casefold()
            if not dedup_key or dedup_key in seen:
                continue

            seen.add(dedup_key)
            normalised.append(
                document.model_copy(
                    update={
                        "title": title,
                        "snippet": snippet,
                        "url": document.url.strip() if document.url else None,
                    }
                )
            )

            if len(normalised) == max_results:
                break

        return normalised
