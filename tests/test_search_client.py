from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import SourceDocument
from multi_agent_research_lab.services.search_client import SearchClient


def test_search_normalises_deduplicates_and_limits_results() -> None:
    def transport(query: str, max_results: int) -> list[SourceDocument]:
        assert query == "Explain multi-agent systems"
        assert max_results == 2
        return [
            SourceDocument(
                title=" Source A ",
                url="https://example.com/a",
                snippet=" First source. ",
            ),
            SourceDocument(
                title="Duplicate source",
                url="https://example.com/a",
                snippet="Duplicate URL.",
            ),
            SourceDocument(
                title="Source B",
                url="https://example.com/b",
                snippet="Second source.",
            ),
        ]

    client = SearchClient(transport=transport)
    results = client.search("Explain multi-agent systems", max_results=2)

    assert [item.title for item in results] == ["Source A", "Source B"]
    assert [item.url for item in results] == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_search_uses_clearly_labelled_mock_when_key_is_missing() -> None:
    settings = Settings(_env_file=None, TAVILY_API_KEY=None)
    results = SearchClient(settings=settings).search(
        "Explain multi-agent systems",
        max_results=2,
    )

    assert len(results) == 2
    assert all(item.metadata["is_mock"] is True for item in results)
