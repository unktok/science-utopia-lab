from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

import jsonschema
import pytest

from utopia.optimization import parallel_benchmark as benchmark


def synthetic_protocol() -> dict:
    return {
        "schema": benchmark.PROTOCOL_SCHEMA,
        "id": "synthetic-test",
        "worker_counts": [1, 2, 4],
        "repetitions": 1,
        "logical_runs": 4,
        "requests_per_run": 1,
        "warmup_requests": 0,
        "request_timeout_seconds": 5,
        "max_retries": 0,
        "sample_interval_seconds": 0.01,
        "cooldown_seconds": 0,
        "seed": 7,
        "workload": {
            "kind": "synthetic",
            "delays_seconds": [0.04],
            "prompt_tokens": 10,
            "generated_tokens": 5,
        },
    }


def test_load_protocol_and_dry_run_budget(tmp_path: Path) -> None:
    protocol = synthetic_protocol()
    source = tmp_path / "protocol.json"
    source.write_text(json.dumps(protocol))

    loaded = benchmark.load_protocol(source)
    plan = benchmark.execution_plan(loaded)

    assert plan["worker_counts"] == [1, 2, 4]
    assert plan["total_requests"] == 12
    assert plan["warmup_requests"] == 0
    assert len(plan["protocol_sha256"]) == 64


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("worker_counts", [1, 1], "unique positive"),
        ("logical_runs", 0, "positive integer"),
        ("warmup_requests", -1, "nonnegative integer"),
    ],
)
def test_invalid_protocol_is_rejected(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    protocol = synthetic_protocol()
    protocol[field] = value
    source = tmp_path / "protocol.json"
    source.write_text(json.dumps(protocol))

    with pytest.raises(ValueError, match=message):
        benchmark.load_protocol(source)


def test_synthetic_report_shows_bounded_scaling_and_validates_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        benchmark,
        "memory_snapshot",
        lambda offset: {
            "offset_seconds": offset,
            "swap_used_bytes": 0,
            "ollama_process_rss_bytes": 100,
        },
    )

    report = benchmark.execute(synthetic_protocol())

    assert report["schema"] == benchmark.REPORT_SCHEMA
    assert [item["workers"] for item in report["aggregates"]] == [1, 2, 4]
    makespans = {
        item["workers"]: item["makespan_seconds"]["mean"]
        for item in report["aggregates"]
    }
    assert makespans[4] < makespans[2] < makespans[1]
    assert report["observations"]["fastest_zero_request_error_worker_count"] == 4
    assert all(item["failed_requests"] == 0 for item in report["aggregates"])
    assert "Engineering observations only" in report["observations"]["interpretation_boundary"]

    schema_path = (
        benchmark.ROOT
        / "research/optimizers/compute/schemas/parallel-benchmark-report-v1.schema.json"
    )
    jsonschema.Draft202012Validator(
        json.loads(schema_path.read_text())
    ).validate(report)


def test_repetition_rotates_worker_order(monkeypatch: pytest.MonkeyPatch) -> None:
    protocol = synthetic_protocol()
    protocol["repetitions"] = 3
    seen: list[tuple[int, int]] = []

    def fake_trial(_protocol, *, workers: int, repetition: int):
        seen.append((repetition, workers))
        return {
            "repetition": repetition,
            "workers": workers,
            "makespan_seconds": 1.0,
            "requests": {"failed": 0, "retries": 0},
            "throughput": {"generated_tokens_per_second": 1.0},
            "request_latency_seconds": {"mean": 1.0},
        }

    monkeypatch.setattr(benchmark, "run_trial", fake_trial)
    benchmark.execute(protocol)

    assert seen == [
        (0, 1), (0, 2), (0, 4),
        (1, 2), (1, 4), (1, 1),
        (2, 4), (2, 1), (2, 2),
    ]


class OllamaFixture(BaseHTTPRequestHandler):
    posts = 0

    def log_message(self, *_args) -> None:
        pass

    def do_POST(self) -> None:
        type(self).posts += 1
        length = int(self.headers["Content-Length"])
        json.loads(self.rfile.read(length))
        if type(self).posts == 1:
            self.send_response(500)
            self.end_headers()
            return
        body = json.dumps({
            "message": {"content": '{"score": 7}'},
            "done": True,
            "done_reason": "stop",
            "total_duration": 100,
            "load_duration": 0,
            "prompt_eval_count": 11,
            "prompt_eval_duration": 20,
            "eval_count": 5,
            "eval_duration": 80,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_ollama_request_records_retry_and_server_counts() -> None:
    OllamaFixture.posts = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), OllamaFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = benchmark._ollama_request(
            {
                "endpoint": f"http://127.0.0.1:{server.server_port}/api/chat",
                "model": "fixture",
                "prompts": ["fixture prompt"],
                "num_predict": 8,
            },
            request_index=0,
            seed=1,
            timeout=5,
            max_retries=1,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["retries"] == 1
    assert result["prompt_tokens"] == 11
    assert result["generated_tokens"] == 5
    assert len(result["response_sha256"]) == 64


def test_vm_stat_parser_preserves_page_size_and_counts() -> None:
    parsed = benchmark._parse_vm_stat(
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages active: 123.\nPages wired down: 45.\n"
    )

    assert parsed == {
        "page_size_bytes": 16384,
        "pages_active": 123,
        "pages_wired_down": 45,
    }


def test_markdown_calls_result_an_observation_not_an_adoption_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        benchmark,
        "memory_snapshot",
        lambda offset: {"offset_seconds": offset},
    )
    report = benchmark.execute(synthetic_protocol())
    text = benchmark.markdown_report(report)

    assert "not an automatic adoption gate" in text
    assert "not rank science systems" in text
