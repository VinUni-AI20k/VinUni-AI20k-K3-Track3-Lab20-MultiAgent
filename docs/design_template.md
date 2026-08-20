# Design Template

## Problem

Hệ thống nhận một câu hỏi nghiên cứu mở, thu thập tối đa 5 nguồn, phân tích các claim và
viết câu trả lời cho người học kỹ thuật kèm citation đánh số.

## Why multi-agent?

Single-agent phù hợp làm baseline nhưng khó quan sát bước nào tạo lỗi. Multi-agent tách tìm kiếm,
phân tích và viết để có thể retry/fallback từng bước, kiểm tra shared state và đánh giá citation.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Chọn bước còn thiếu và dừng workflow | Toàn bộ shared state | Route kế tiếp | Route lặp hoặc vượt giới hạn |
| Researcher | Tìm, lọc trùng và đánh số nguồn | Query, `max_sources` | Sources, research notes | Search timeout/không có key |
| Analyst | Tách claim và đánh giá giới hạn bằng chứng | Sources, research notes | Analysis notes | Nguồn ít hoặc yếu |
| Writer | Tổng hợp theo audience, giữ citation | Query, analysis, sources | Final answer | LLM timeout hoặc output rỗng |

## Shared state

- `request`: input đã validate và số nguồn tối đa.
- `route_history`, `iteration`: audit quyết định và chặn vòng lặp.
- `sources`, `research_notes`, `analysis_notes`, `final_answer`: artifact handoff rõ ràng.
- `agent_results`: nội dung và usage theo agent để benchmark.
- `trace`, `errors`: thời gian, attempt và failure để debug.

## Routing policy

`START → supervisor → researcher → supervisor → analyst → supervisor → writer → supervisor → END`.
Supervisor chọn field còn thiếu; mọi worker quay lại supervisor. Workflow dừng theo `done`,
`max_iterations` hoặc `timeout_seconds`.

## Guardrails

- Max iterations: 6 mặc định, cấu hình qua `MAX_ITERATIONS`.
- Timeout: 60 giây mặc định, kiểm tra ở mỗi vòng workflow và provider call.
- Retry: tối đa 2 lần cho worker; LLM client retry 3 lần với exponential backoff.
- Fallback: writer dùng evidence đã thu thập; không có key thì dùng offline synthesis có nhãn.
- Validation: Pydantic kiểm tra query tối thiểu 5 ký tự, `max_sources` và metric ranges.

## Benchmark plan

Ba query trong `configs/lab_default.yaml` được chạy cho baseline và multi-agent. Metric gồm latency,
estimated cost, structural quality 0–10, citation coverage và failure rate. Kỳ vọng baseline nhanh
hơn; multi-agent có trace/handoff rõ hơn và citation coverage cao hơn trên câu hỏi phức tạp.
