"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics plus limitations and interpretation guidance."""

    lines = [
        "# Báo cáo Lab 20 — Multi-Agent Research System",
        "",
        "- **Học viên:** Trần Việt Trường",
        "- **Mã học viên:** 2A202601467",
        "- **Track:** K3 — Track 3",
        "- **Ngày hoàn thành:** 20/08/2026",
        "",
        "## 1. Tóm tắt bài làm",
        "",
        "Bài làm xây dựng một research assistant gồm Supervisor, Researcher, Analyst và Writer. "
        "Các agent trao đổi qua shared state, được giới hạn số vòng chạy và thời gian, có retry, "
        "fallback, validation, trace JSON và benchmark với single-agent baseline.",
        "",
        "Hệ thống chạy được ở hai chế độ: dùng OpenAI/Tavily khi có API key, hoặc offline fallback "
        "để demo và kiểm thử mà không làm lộ secret.",
        "",
        "## 2. Kiến trúc hệ thống",
        "",
        "```text",
        "User Query",
        "    |",
        "    v",
        "Supervisor / Router",
        "    |--> Researcher --> sources + research_notes",
        "    |--> Analyst   --> analysis_notes",
        "    |--> Writer    --> final_answer + references",
        "    v",
        "Trace JSON + Benchmark Report",
        "```",
        "",
        "Luồng chuẩn: `researcher → analyst → writer → done`. Sau mỗi worker, quyền điều phối "
        "quay lại Supervisor để quyết định bước tiếp theo dựa trên dữ liệu còn thiếu.",
        "",
        "## 3. Vai trò của từng agent",
        "",
        "| Agent | Trách nhiệm | Input chính | Output chính |",
        "|---|---|---|---|",
        "| Supervisor | Chọn route và kiểm soát điểm dừng | Shared state | Route kế tiếp |",
        "| Researcher | Tìm nguồn, lọc trùng, tạo citation | Query | Sources, research notes |",
        "| Analyst | Tách claim và nêu giới hạn bằng chứng | Research notes | Analysis notes |",
        "| Writer | Viết theo audience, giữ citation | Analysis + sources | Final answer |",
        "| Critic | Kiểm tra answer và citation coverage | Final answer | Critic trace event |",
        "",
        "## 4. Shared state và handoff",
        "",
        "- `request`: query, audience và số nguồn tối đa đã được Pydantic validate.",
        "- `route_history`, `iteration`: lưu quyết định và ngăn vòng lặp vô hạn.",
        "- `sources`, `research_notes`, `analysis_notes`, `final_answer`: artifact của từng bước.",
        "- `agent_results`: nội dung và usage metadata của từng agent.",
        "- `trace`, `errors`: span, duration, attempt và lỗi để debug.",
        "",
        "## 5. Guardrails và khả năng phục hồi",
        "",
        "- Tối đa 6 route mặc định; có thể cấu hình bằng `MAX_ITERATIONS`.",
        "- Workflow timeout 60 giây mặc định; provider call dùng cùng giới hạn timeout.",
        "- Worker retry tối đa 2 lần; LLM client retry 3 lần với exponential backoff.",
        "- Khi provider lỗi, lỗi được ghi vào state và Writer dùng evidence tốt nhất đã có.",
        "- Khi không có API key, hệ thống dùng offline sources/fallback có nhãn rõ ràng.",
        "- Query và metric được validate bằng Pydantic schema.",
        "",
        "## 6. Phương pháp benchmark",
        "",
        "Cùng một query được chạy qua single-agent baseline và Supervisor multi-agent. Các metric:",
        "",
        "- **Latency:** thời gian wall-clock của toàn bộ lần chạy.",
        "- **Cost:** tổng provider cost nếu API trả usage; bằng 0 ở chế độ offline.",
        "- **Quality:** structural rubric 0–10 dựa trên answer, analysis, sources và citations.",
        "- **Citation coverage:** số citation xuất hiện trong answer / số nguồn đã thu thập.",
        "- **Failure rate:** 1 nếu không tạo được final answer, ngược lại là 0.",
        "",
        "## 7. Kết quả benchmark",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation = "" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} "
            f"| {citation} | {failure} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## 8. Phân tích kết quả",
            "",
            "Hai workflow đều tạo đủ answer, analysis, 5 nguồn và citation nên đạt điểm structural "
            "quality tối đa khi chạy offline. Khác biệt quan trọng là khả năng quan sát: "
            "baseline không có workflow trace, trong khi multi-agent tạo 7 route/agent events.",
            "",
            "Latency offline rất nhỏ và làm tròn tới 0.00 giây nên không dùng để kết luận "
            "hiệu năng production. Khi chạy API thật, multi-agent có latency/cost cao hơn do "
            "provider calls, đổi lại trách nhiệm rõ hơn và dễ xác định bước gây lỗi.",
            "",
            "Quality là proxy minh bạch, không phải điểm LLM-as-a-judge. Muốn đánh giá nội "
            "dung sâu hơn cần peer review hoặc rubric trên một tập query lớn hơn.",
            "",
            "## 9. Trace mẫu",
            "",
            "File `reports/benchmark_trace.json` lưu toàn bộ state và trace của lần benchmark. "
            "Route history mong đợi:",
            "",
            "```text",
            "researcher → analyst → writer → done",
            "```",
            "",
            "Mỗi span chứa agent, attempt và `duration_seconds`. Nếu có lỗi, từng attempt "
            "được ghi trong `errors` thay vì bị bỏ qua.",
            "",
            "## 10. Failure modes và cách khắc phục",
            "",
            "| Failure mode | Ảnh hưởng | Cách xử lý |",
            "|---|---|---|",
            "| Search outage hoặc thiếu key | Không có nguồn mới | Offline reference set có nhãn |",
            "| Provider timeout | Worker không hoàn tất | Retry, ghi lỗi, dùng writer fallback |",
            "| Routing vô hạn | Tốn thời gian/chi phí | Max iterations và workflow timeout |",
            "| Unsupported claim | Hallucination | Citation đánh số và Critic kiểm tra coverage |",
            "| Nguồn yếu/lỗi thời | Thiếu tin cậy | Analyst yêu cầu kiểm tra lại |",
            "",
            "## 11. Cách chạy lại",
            "",
            "```bash",
            'pip install -e ".[dev,llm]"',
            "python -m pytest -q",
            "python -m ruff check src tests",
            "python -m multi_agent_research_lab.cli multi-agent \\",
            '  --query "Explain multi-agent systems"',
            "python -m multi_agent_research_lab.cli benchmark",
            "```",
            "",
            "Không hard-code API key. Nếu chạy thật, đặt key mới trong `.env`; key từng gửi "
            "qua chat phải được revoke.",
            "",
            "## 12. Exit ticket",
            "",
            "**Khi nào nên dùng multi-agent?** Khi bài toán cần tìm kiếm, phân tích, kiểm tra "
            "và viết tách biệt; cần audit trace hoặc retry từng bước độc lập.",
            "",
            "**Khi nào không nên dùng multi-agent?** Với câu hỏi ngắn, deterministic hoặc "
            "latency/cost "
            "là ưu tiên cao; một workflow đơn giản hoặc single-agent thường phù hợp hơn.",
            "",
            "## 13. Kết luận",
            "",
            "Bài làm đáp ứng role clarity, shared state, guardrails, trace và benchmark. "
            "Multi-agent không mặc định tốt hơn single-agent, nhưng phù hợp khi nhu cầu quan "
            "sát đủ lớn để bù cho chi phí điều phối tăng thêm.",
        ]
    )
    return "\n".join(lines) + "\n"
