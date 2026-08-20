# Design Template

## Problem

The system answers research questions by collecting web sources, extracting
evidence, analyzing claims, and writing a concise answer with verifiable source
references. It supports both a one-call baseline and a supervised multi-agent
workflow for comparison.

## Why multi-agent?

A single agent is cheaper and faster for short, self-contained questions, but it
must perform search, evidence review, synthesis, and writing in one call. A
multi-agent workflow separates these responsibilities so sources can be
inspected, claims can be challenged, and the final answer can preserve source
references and an auditable trace. The extra coordination and LLM calls are
justified when grounding and auditability matter more than minimum latency/cost.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Select the next worker and stop safely | Shared `ResearchState` | `next_route`, route trace | Timeout/max-iteration stop; retry once then fallback |
| Researcher | Search and summarize source-backed evidence | Query and `max_sources` | `sources`, `research_notes`, usage | `researcher:` error; retry once, then `done` |
| Analyst | Extract claims, compare viewpoints, flag uncertainty | Sources and research notes | `analysis_notes`, usage | `analyst:` error; retry once, then fallback to writer |
| Writer | Produce the final answer and verified references | Analysis/research context and sources | `final_answer` with `## Sources`, usage | `writer:` error; retry once, then `done` |

## Shared state

`ResearchState` is the single handoff contract. It contains the request,
iteration and `next_route`, route history, sources, research/analysis/final
outputs, per-agent results, local trace events, errors, token usage, estimated
cost, priced-call count, retry counts, and `started_at` for timeout checks.
Workers mutate this state instead of passing unstructured results between
nodes.

## Routing policy

```text
START -> supervisor
supervisor -> researcher  when sources/research notes are missing
researcher -> supervisor
supervisor -> analyst     when analysis notes are missing
analyst -> supervisor
supervisor -> writer      when final answer is missing
writer -> supervisor
supervisor -> END         when answer is complete, timed out, or exhausted
```

Worker errors use the prefixes `researcher:`, `analyst:`, and `writer:`. The
Supervisor detects these prefixes and allows one retry per worker before using
the configured fallback route.

## Guardrails

- Max iterations: `MAX_ITERATIONS` (default 6, bounded by configuration).
- Timeout: `TIMEOUT_SECONDS` checked by the Supervisor using `started_at`.
- Retry: one retry per failed worker; provider clients separately retry only
  transient network, timeout, rate-limit, and server errors.
- Fallback: researcher failure goes to `done`; analyst failure falls back to
  `writer`; writer failure goes to `done`.
- Validation: Pydantic validates request/state schemas; empty search queries,
  invalid result limits, and empty LLM responses raise domain errors.

## Benchmark plan

The default benchmark uses three queries covering GraphRAG research, customer
support architecture, and production guardrails. Each query runs once through
the single-agent baseline and once through the multi-agent workflow. Automatic
metrics are latency, estimated OpenAI token cost, citation coverage, and
failure rate. Quality is manually scored with relevance (3), grounding (3),
clarity (2), and citation quality (2). Expected trade-off: multi-agent should
improve grounding/citations and resilience while using more calls, latency,
and cost.
