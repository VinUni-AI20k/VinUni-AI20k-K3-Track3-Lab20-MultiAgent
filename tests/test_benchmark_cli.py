from pathlib import Path

import pytest

from multi_agent_research_lab.cli import _load_benchmark_queries


def test_load_benchmark_queries_returns_three_queries(tmp_path: Path) -> None:
    config = tmp_path / "valid.yaml"
    config.write_text(
        "benchmark:\n  queries:\n    - First query\n    - Second query\n    - Third query\n",
        encoding="utf-8",
    )

    assert _load_benchmark_queries(config) == [
        "First query",
        "Second query",
        "Third query",
    ]


def test_load_benchmark_queries_rejects_missing_benchmark(tmp_path: Path) -> None:
    config = tmp_path / "missing.yaml"
    config.write_text("other: {}\n", encoding="utf-8")

    with pytest.raises(Exception, match="Missing benchmark section"):
        _load_benchmark_queries(config)


def test_load_benchmark_queries_rejects_empty_queries(tmp_path: Path) -> None:
    config = tmp_path / "empty.yaml"
    config.write_text("benchmark:\n  queries: []\n", encoding="utf-8")

    with pytest.raises(Exception, match="non-empty string list"):
        _load_benchmark_queries(config)


def test_load_benchmark_queries_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="Cannot read config"):
        _load_benchmark_queries(tmp_path / "does-not-exist.yaml")
