# Benchmark Report

| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| single-agent baseline | 0.00 | 0.0000 | 10.0 | 100% | 0% | 5 sources; 0 trace events |
| supervisor multi-agent | 0.00 | 0.0000 | 10.0 | 100% | 0% | 5 sources; 7 trace events |

## Interpretation

Quality is a transparent structural proxy (answer, analysis, sources, citations), not an LLM judge.
Latency and cost depend on provider/network conditions; rerun on the same queries for comparison.

## Known failure modes and mitigations

- Search outage or missing key: use the labelled offline reference set and disclose limitations.
- Provider timeout: retry twice, record the error, then use the best available writer fallback.
- Infinite routing: enforce maximum iterations and workflow timeout.
- Unsupported claims: retain numbered sources and run the citation critic.
