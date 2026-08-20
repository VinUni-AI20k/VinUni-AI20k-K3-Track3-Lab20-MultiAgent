# Hướng dẫn hoàn thành Lab 20 — Multi-Agent Research System

Tài liệu này hướng dẫn hoàn thành bài lab từ starter repo đến artefact nộp bài. Làm theo thứ tự; mỗi bước đều nêu rõ mục đích, file cần sửa, cách làm và điều kiện kiểm tra.

## 1. Mục tiêu và đầu ra

Xây dựng hai cách trả lời một câu hỏi research:

1. **Single-agent baseline**: một lần gọi LLM để trả lời toàn bộ câu hỏi.
2. **Multi-agent workflow**: `Supervisor -> Researcher -> Analyst -> Writer`.

Sau đó chạy cùng một bộ query và so sánh ít nhất latency, chi phí ước tính và chất lượng. Bài hoàn tất khi có:

- CLI baseline và multi-agent chạy không còn `StudentTodoError` ở luồng chính.
- Trace của ít nhất một lượt chạy multi-agent.
- `reports/benchmark_report.md` có số liệu và phân tích failure mode.
- `ruff`, `mypy`, `pytest` đều pass.
- Câu trả lời exit ticket và tài liệu thiết kế.

> `CriticAgent` là phần nâng cao. Không đưa vào luồng bắt buộc trước khi bốn agent chính hoàn chỉnh.

## 2. Kiến trúc mục tiêu

```text
User query
    |
    v
Supervisor -- thiếu nguồn ------> Researcher -- sources, research_notes --+
    ^                                                                  |
    |                                                                  v
    +----------- thiếu phân tích ---- Analyst -- analysis_notes -------+
    |
    +----------- đủ ngữ cảnh -------> Writer -- final_answer + citations
    |
    +----------- done / timeout / max iterations --> Kết thúc
```

Mỗi agent chỉ có một trách nhiệm:

| Thành phần | Trách nhiệm | Không nên làm |
|---|---|---|
| `SupervisorAgent` | Chọn bước tiếp theo, áp guardrail | Tìm kiếm hoặc viết câu trả lời dài |
| `ResearcherAgent` | Lấy, lọc và ghi nguồn/ghi chú | Ra kết luận cuối cùng |
| `AnalystAgent` | Đánh giá bằng chứng, so sánh, nêu hạn chế | Bịa nguồn mới |
| `WriterAgent` | Tổng hợp cho đúng audience, gắn citation | Quyết định route |
| Services | Gọi provider, retry, timeout, usage | Chứa business logic của agent |
| Workflow | Nối node và conditional edge | Viết prompt dài |

## 3. Bước 0 — Chuẩn bị môi trường

**Mục đích:** cài package editable để lệnh CLI import được package trong `src/`, đồng thời cài các công cụ kiểm tra.

Trong PowerShell, tại thư mục gốc repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,llm]"
Copy-Item .env.example .env
```

Nếu PowerShell chặn activate script, chỉ áp dụng cho terminal hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Mở `.env` và điền ít nhất:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

`TAVILY_API_KEY` và key LangSmith/Langfuse có thể để trống lúc đầu vì ta sẽ có mock fallback. Không commit `.env`.

Kiểm tra:

```powershell
python -m multi_agent_research_lab.cli --help
python -m pytest
python -m ruff check src tests
python -m mypy src
```

**Đạt khi:** CLI không còn `ModuleNotFoundError`; các lệnh kiểm tra chạy được. Test hiện tại pass chỉ vì nó kiểm tra skeleton, chưa phải bằng chứng bài đã hoàn thành.

## 4. Bước 1 — Ghi nhận điểm xuất phát và tạo nhánh

**Mục đích:** không nhầm lẫn giữa code đã làm và TODO của starter.

```powershell
git switch -c feat/multi-agent-research
rg -n "TODO\(student\)|StudentTodoError" src tests docs
```

Các TODO bắt buộc nằm trong:

- `services/llm_client.py`, `services/search_client.py`;
- `agents/supervisor.py`, `researcher.py`, `analyst.py`, `writer.py`;
- `graph/workflow.py`;
- baseline trong `cli.py`;
- tracing và benchmark/report.

**Lưu ý quan trọng:** `tests/test_agents_todo.py` cố tình đòi Supervisor ném lỗi TODO. Khi Supervisor được triển khai, phải thay test này bằng test routing thực tế, không được giữ nguyên.

## 5. Bước 2 — Hoàn thiện config, schema và shared state

**Mục đích:** tạo một hợp đồng dữ liệu rõ ràng để agent handoff mà không mất context và để benchmark lấy được usage/cost.

Sửa `core/schemas.py` và `core/state.py`. Giữ các field hiện có, sau đó cân nhắc thêm:

| Field | Kiểu gợi ý | Mục đích |
|---|---|---|
| `next_route` | `str | None` | Kết quả route mới nhất để conditional edge đọc |
| `started_at` / `deadline` | số monotonic hoặc datetime | Kiểm tra timeout toàn workflow |
| `input_tokens`, `output_tokens`, `estimated_cost_usd` | số | Tổng usage từ mọi LLM call |
| `retry_counts` | `dict[str, int]` | Giới hạn retry theo agent/service |
| trace event | name, payload, duration, timestamp | Debug và chứng minh trace |

Quy ước nên dùng:

- `sources` chỉ chứa `SourceDocument` có title và snippet không rỗng.
- Agent không tự xóa output hợp lệ của agent trước.
- `errors` lưu thông điệp có agent/loại lỗi; không chứa API key hay prompt nhạy cảm.
- `record_route()` tăng iteration cho mỗi worker được chọn. Thống nhất việc có hoặc không ghi `done` vào history, rồi viết test theo quy ước đó.

Thêm helper nhỏ, ví dụ `add_usage(response)` và `has_timed_out()`, để agent không lặp code cộng token/cost.

**Đạt khi:** có thể tạo `ResearchState`, thêm nguồn, route và trace; Pydantic validate được dữ liệu sai rõ ràng.

## 6. Bước 3 — Implement LLM client

**Mục đích:** tập trung toàn bộ provider-specific code, retry, timeout và đo usage ở một nơi. Agent không được import SDK trực tiếp.

Sửa `services/llm_client.py` theo thiết kế sau:

1. `LLMClient.__init__` nhận `Settings` (mặc định `get_settings()`), hoặc nhận một client đã inject để test.
2. Nếu không có `OPENAI_API_KEY`, ném `AgentExecutionError` có thông điệp hướng dẫn, không ném lỗi mơ hồ.
3. `complete(system_prompt, user_prompt)` gọi SDK, đặt timeout theo `settings.timeout_seconds`, dùng retry có giới hạn của `tenacity` cho lỗi tạm thời.
4. Trả về `LLMResponse(content, input_tokens, output_tokens, cost_usd)`; usage không có thì để `None`, không tự đoán là 0.
5. Log model, latency và usage; tuyệt đối không log API key hoặc toàn bộ prompt chứa dữ liệu nhạy cảm.

Để tính `cost_usd`, dùng bảng giá được cấu hình rõ theo model hoặc để `None` nếu không xác định được. Không coi chi phí là chính xác khi provider không trả usage.

### Mock cho test

Tạo fake client trong test hoặc fixture có `complete()` trả `LLMResponse` cố định. Fake phải:

- không gọi mạng;
- có thể trả nội dung khác nhau cho analyst/writer;
- có token/cost giả lập để test phép cộng usage.

**Đạt khi:** test `LLMClient` bao phủ thiếu key, success mapping usage và lỗi retry/failure; code agent chỉ phụ thuộc interface `complete()`.

## 7. Bước 4 — Implement Search client

**Mục đích:** Researcher nhận nguồn có cấu trúc, thay vì một chuỗi tự do khó trích dẫn.

Sửa `services/search_client.py`:

1. Cài/thiết lập provider bạn chọn (Tavily là lựa chọn theo `.env.example`) hoặc gọi HTTP API có timeout.
2. Map kết quả sang `SourceDocument(title, url, snippet, metadata)`.
3. Cắt về `max_results`, loại kết quả thiếu title/snippet, loại URL trùng.
4. Lỗi provider phải trở thành `AgentExecutionError` hoặc kết quả fallback có trace rõ ràng.
5. Khi không có key, dùng **mock source rõ ràng là mock** cho test/demo; không trình bày nó là nguồn web thật trong benchmark nộp bài.

**Đạt khi:** `SearchClient.search()` trả danh sách source hợp lệ; test bao phủ lọc trùng, max_results, lỗi provider và fallback.

## 8. Bước 5 — Hoàn thiện single-agent baseline

**Mục đích:** có đối chứng công bằng: một LLM call xử lý cùng query, không gọi workflow nhiều agent.

Sửa command `baseline` trong `cli.py`:

1. Parse `ResearchQuery` như hiện có.
2. Tạo `ResearchState`.
3. Gọi `LLMClient.complete()` đúng một lần với prompt yêu cầu trả lời cho `request.audience`.
4. Gán `final_answer`, append một `AgentResult`, trace latency/usage và in output.
5. Bắt `AgentExecutionError` để CLI báo lỗi thân thiện với exit code khác 0.

Không cho baseline âm thầm dùng SearchClient, nếu không benchmark sẽ không còn là single-agent baseline tối giản.

Kiểm tra:

```powershell
python -m multi_agent_research_lab.cli baseline --query "Explain multi-agent systems"
```

**Đạt khi:** output không chứa placeholder/TODO và state có usage/latency khi provider trả dữ liệu.

## 9. Bước 6 — Implement SupervisorAgent

**Mục đích:** tạo router có thể dự đoán được, dễ test và không lặp vô hạn.

Sửa `agents/supervisor.py`. Routing policy tối thiểu:

```text
if hết timeout hoặc iteration >= max_iterations: done
elif chưa có sources hoặc research_notes: researcher
elif chưa có analysis_notes: analyst
elif chưa có final_answer: writer
else: done
```

Khi một worker thất bại, dùng policy tường minh, ví dụ:

- retry cùng worker tối đa một lần nếu lỗi tạm thời;
- nếu researcher không lấy được nguồn sau retry, chuyển writer để trả lời có cảnh báo giới hạn bằng chứng;
- nếu analyst lỗi nhưng đã có `research_notes`, cho writer dùng research notes;
- writer lỗi thì kết thúc failed, không lặp lại vô hạn.

Supervisor phải đặt `next_route`, gọi `record_route()` cho worker route và ghi trace `supervisor.route`. Không gọi worker trực tiếp trong class này.

**Đạt khi:** unit test bao phủ bốn route bình thường, max iteration, timeout và một fallback lỗi.

## 10. Bước 7 — Implement ba worker agent

### 7.1 ResearcherAgent

**Mục đích:** thu thập nguồn và viết ghi chú factual ngắn cho bước sau.

Trong `agents/researcher.py`:

1. Gọi `SearchClient.search(state.request.query, state.request.max_sources)`.
2. Validate có nguồn; nếu rỗng, ghi error/trace theo fallback policy.
3. Gán `state.sources`.
4. Tạo `research_notes`: mỗi nguồn cần có claim/snippet, title và URL/index. Có thể dùng LLM để tóm tắt, nhưng phải giữ liên kết tới source gốc.
5. Append `AgentResult(agent=RESEARCHER, ...)` và trace `researcher.done`.

### 7.2 AnalystAgent

**Mục đích:** biến nguồn/ghi chú thành insight đáng tin hơn, không chỉ nối các đoạn văn.

Trong `agents/analyst.py`:

1. Guard: không có sources/research_notes thì ghi lỗi và return có kiểm soát.
2. Gọi LLM với prompt yêu cầu: claim chính, điểm đồng/khác, độ tin cậy, thiếu bằng chứng và điều không nên khẳng định.
3. Gán `analysis_notes`; cộng usage; append `AgentResult(ANALYST, ...)`; trace `analyst.done`.

### 7.3 WriterAgent

**Mục đích:** trả lời trực tiếp câu hỏi cho audience, dựa trên dữ liệu đã có và có citation kiểm chứng được.

Trong `agents/writer.py`:

1. Dùng `analysis_notes`, fallback sang `research_notes` nếu cần.
2. Gọi LLM với yêu cầu không tạo nguồn mới và phân biệt fact với inference.
3. Tạo citation list từ `state.sources`, ví dụ `[1] Title (URL)`; chỉ gắn citation có thật.
4. Gán `final_answer`; append result, usage và trace `writer.done`.

**Đạt khi:** mỗi worker có test success, thiếu input và lỗi service. Luồng thành công tạo đủ `sources`, `research_notes`, `analysis_notes`, `final_answer`.

## 11. Bước 8 — Build MultiAgentWorkflow bằng LangGraph

**Mục đích:** quản lý thứ tự chạy bằng graph thay vì vòng lặp rải rác trong CLI.

Sửa `graph/workflow.py`:

1. Khởi tạo/inject `SupervisorAgent`, ba worker và Settings để test thay bằng fake dễ dàng.
2. `build()` tạo `StateGraph` với node: `supervisor`, `researcher`, `analyst`, `writer`.
3. Edge bắt đầu đi vào supervisor.
4. Conditional edge từ supervisor đọc `state.next_route`: đi tới worker tương ứng hoặc `END` khi `done`.
5. Mỗi worker có edge quay lại supervisor.
6. `run()` compile graph, invoke bằng state, rồi chuyển kết quả về `ResearchState` nếu cần.

Đừng để node vừa quyết định route vừa chạy nhiều worker. Đừng import LangGraph ở cấp module nếu muốn test không có extra `llm`; lựa chọn đơn giản hơn là đảm bảo CI cài `.[dev,llm]`.

Kiểm tra:

```powershell
python -m multi_agent_research_lab.cli multi-agent --query "Compare single-agent and multi-agent workflows for customer support"
```

**Đạt khi:** output có answer, sources, trace, route history theo policy; workflow dừng trong giới hạn; không có `StudentTodoError`.

## 12. Bước 9 — Tracing và logging

**Mục đích:** có bằng chứng hệ thống chạy và có khả năng debug.

Giữ `trace_span()` trong `observability/tracing.py` làm local trace. Mỗi span tối thiểu ghi:

- agent/service name;
- route, số iteration và kết quả success/failure;
- duration;
- token/cost nếu có;
- không ghi API key hoặc nội dung nhạy cảm.

Khi có LangSmith hoặc Langfuse key, cấu hình provider qua `.env` và bọc workflow/LLM call trong span provider. Chạy một query thật, mở UI và lưu screenshot/link.

**Đạt khi:** `state.trace` giải thích được ai làm gì theo thứ tự; có một trace evidence dùng cho bài nộp.

## 13. Bước 10 — Benchmark và báo cáo

**Mục đích:** trả lời bằng dữ liệu câu hỏi "multi-agent có đáng dùng không?".

Sửa `evaluation/benchmark.py` để `run_benchmark()`:

1. Chạy runner và đo wall-clock latency, kể cả lỗi.
2. Lấy tổng usage/cost trong state.
3. Tính citation coverage: số citation/source được nhắc hợp lệ chia số nguồn dùng được. Định nghĩa cách tính trong report.
4. Ghi failure rate cho nhiều query: `số run lỗi / tổng run`.
5. Quality dùng rubric 0–10 do peer review/human chấm; không tự gọi đây là ground truth nếu do LLM chấm.

Dùng ba query trong `configs/lab_default.yaml`; chạy **cùng query, model, max_sources và điều kiện mạng** cho baseline và multi-agent. Lặp mỗi query ít nhất ba lần nếu thời gian/chi phí cho phép và báo cáo trung bình, hoặc nói rõ nếu chỉ có một run.

Tạo `reports/benchmark_report.md` theo cấu trúc:

```markdown
# Benchmark Report

## Setup
- model, date, number of runs, provider, source mode

## Results
| Query | Approach | Latency | Cost | Quality | Citation coverage | Success |

## Interpretation
- Khi multi-agent cải thiện chất lượng/citation?
- Trade-off latency và chi phí là gì?

## Failure mode and fix
- Một lỗi thực tế, nguyên nhân, trace evidence và cách sửa.
```

Không điền số liệu giả làm kết quả thực tế. Nếu thiếu API key, ghi rõ benchmark là mock/demo và thực hiện lại trước khi nộp.

## 14. Bước 11 — Tests, chất lượng mã và CI

**Mục đích:** chứng minh logic đúng mà không tốn API call trong CI.

Thay `tests/test_agents_todo.py` bằng test thực. Bổ sung tối thiểu:

| Nhóm test | Case bắt buộc |
|---|---|
| Settings | default, env override, validation max iterations |
| Services | mapping success, thiếu key, timeout/failure, mock fallback |
| Supervisor | 4 route, max iteration, timeout, fallback lỗi |
| Workers | success và thiếu input cho từng agent |
| Workflow | happy path, dừng max iteration, worker failure không lặp vô hạn |
| Evaluation | latency, cost aggregation, citation coverage, report rendering |
| CLI | baseline/multi-agent exit code và output bằng dependency fake |

Chạy trước khi commit:

```powershell
python -m ruff format src tests
python -m ruff check src tests
python -m mypy src
python -m pytest
```

`ci.yml` hiện chỉ cài `.[dev]`. Nếu workflow import LangGraph ở module level, đổi bước cài của CI thành:

```yaml
pip install -e ".[dev,llm]"
```

## 15. Bước 12 — Hoàn thiện tài liệu và nộp bài

1. Điền [design_template.md](design_template.md): problem, lý do dùng multi-agent, vai trò, state, routing, guardrail và benchmark plan.
2. Tạo `reports/exit_ticket.md` trả lời:
   - Khi nào nên dùng multi-agent, vì sao?
   - Khi nào không nên dùng multi-agent, vì sao?
3. Cập nhật README: cách setup Windows, cách chạy lệnh, mô tả fallback và thống nhất thời lượng lab thành **240 phút** (README hiện ghi 2 giờ, không khớp codelab/slide).
4. Commit theo từng phần nhỏ và kiểm tra `git status` trước khi push.

Gợi ý commit:

```text
chore: set up local development environment
feat: add resilient llm and search clients
feat: implement supervisor and research worker agents
feat: add langgraph multi-agent workflow
feat: add tracing and benchmark evaluation
test: cover agent routing and workflow guardrails
docs: add benchmark report and lab design
```

## 16. Checklist cuối cùng

- [ ] `.env` không bị commit.
- [ ] `python -m multi_agent_research_lab.cli baseline --query "..."` trả lời không còn placeholder.
- [ ] `python -m multi_agent_research_lab.cli multi-agent --query "..."` hoàn thành và có `route_history`.
- [ ] Không còn `StudentTodoError` trong luồng bắt buộc.
- [ ] Worker không tạo citation không có trong `state.sources`.
- [ ] Có timeout, max iteration, retry/fallback và validation được test.
- [ ] Có trace screenshot/link của lượt chạy thật.
- [ ] `reports/benchmark_report.md` có latency, cost, quality và failure mode.
- [ ] `ruff`, `mypy`, `pytest` pass.
- [ ] Có design và exit ticket.

## 17. Troubleshooting nhanh

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: multi_agent_research_lab` | Chưa cài package editable | Activate `.venv`, chạy `pip install -e ".[dev,llm]"` |
| `401`/thiếu API key | `.env` chưa có key hoặc sai key | Kiểm tra `.env`; không hard-code key |
| Graph lặp vô hạn | Không tăng iteration hoặc router không trả `done` | Test max iteration; ghi `next_route` và trace mọi route |
| CI lỗi import `langgraph` | CI chỉ cài `.[dev]` | Cài `.[dev,llm]` hoặc lazy import |
| Test gọi mạng/tốn tiền | Không inject fake services | Dùng fixture fake LLM/Search |
| Citation coverage thấp | Writer không dùng danh sách nguồn có cấu trúc | Tạo citation list từ `state.sources`, test nó |
| Trace không thấy | Chưa cấu hình key/provider | Kiểm tra `.env`, giữ JSON trace local để debug |

---

Làm theo thứ tự từ Bước 0 đến Bước 12. Khi gặp lỗi, ưu tiên viết hoặc điều chỉnh test tái hiện lỗi trước, sau đó mới sửa implementation.
