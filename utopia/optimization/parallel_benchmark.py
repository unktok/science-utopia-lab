"""Measure bounded logical-run concurrency against one inference endpoint.

This is an engineering benchmark.  It does not evaluate scientific outcomes and
it does not choose an optimization objective.  A fixed workload is replayed at
each configured worker count so throughput, latency, failures, retries, and host
memory pressure can be compared before a long campaign is scheduled.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import threading
import time
from typing import Any, Mapping
from urllib import error as urlerror
from urllib import request as urlrequest


ROOT = Path(__file__).resolve().parents[2]
REPORT_SCHEMA = "science-utopia.parallel-benchmark-report.v1"
PROTOCOL_SCHEMA = "science-utopia.parallel-benchmark-protocol.v1"
OLLAMA_ENV_ALLOWLIST = (
    "OLLAMA_CONTEXT_LENGTH",
    "OLLAMA_FLASH_ATTENTION",
    "OLLAMA_HOST",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_KV_CACHE_TYPE",
    "OLLAMA_MAX_LOADED_MODELS",
    "OLLAMA_MAX_QUEUE",
    "OLLAMA_NUM_PARALLEL",
    "OLLAMA_SCHED_SPREAD",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def load_protocol(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    protocol = json.loads(source.read_text(encoding="utf-8"))
    if protocol.get("schema") != PROTOCOL_SCHEMA:
        raise ValueError(f"protocol.schema must be {PROTOCOL_SCHEMA!r}")
    if not isinstance(protocol.get("id"), str) or not protocol["id"]:
        raise ValueError("protocol.id must be a non-empty string")
    workers = protocol.get("worker_counts")
    if (
        not isinstance(workers, list)
        or not workers
        or any(type(item) is not int or item < 1 for item in workers)
        or len(workers) != len(set(workers))
    ):
        raise ValueError("worker_counts must contain unique positive integers")
    _positive_int(protocol.get("repetitions"), "repetitions")
    _positive_int(protocol.get("logical_runs"), "logical_runs")
    _positive_int(protocol.get("requests_per_run"), "requests_per_run")
    timeout = protocol.get("request_timeout_seconds")
    if type(timeout) not in {int, float} or timeout <= 0:
        raise ValueError("request_timeout_seconds must be positive")
    retries = protocol.get("max_retries")
    if type(retries) is not int or retries < 0:
        raise ValueError("max_retries must be a nonnegative integer")
    warmup = protocol.get("warmup_requests", 0)
    if type(warmup) is not int or warmup < 0:
        raise ValueError("warmup_requests must be a nonnegative integer")
    interval = protocol.get("sample_interval_seconds")
    if type(interval) not in {int, float} or interval <= 0:
        raise ValueError("sample_interval_seconds must be positive")
    workload = protocol.get("workload")
    if not isinstance(workload, dict) or workload.get("kind") not in {
        "synthetic",
        "ollama_chat",
    }:
        raise ValueError("workload.kind must be synthetic or ollama_chat")
    if workload["kind"] == "synthetic":
        delays = workload.get("delays_seconds")
        if (
            not isinstance(delays, list)
            or not delays
            or any(type(item) not in {int, float} or item < 0 for item in delays)
        ):
            raise ValueError("synthetic workload requires nonnegative delays_seconds")
        _positive_int(workload.get("generated_tokens", 1), "generated_tokens")
    else:
        for key in ("endpoint", "model", "prompts"):
            if not workload.get(key):
                raise ValueError(f"ollama_chat workload.{key} is required")
        if not isinstance(workload["prompts"], list) or not all(
            isinstance(item, str) and item for item in workload["prompts"]
        ):
            raise ValueError("ollama_chat workload.prompts must contain strings")
        _positive_int(workload.get("num_predict"), "workload.num_predict")
        parsed_endpoint = str(workload["endpoint"])
        if not parsed_endpoint.startswith(("http://", "https://")):
            raise ValueError("workload.endpoint must be an HTTP(S) URL")
    return protocol


def _run_command(command: list[str], *, timeout: float = 5) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip()


def _sysctl(name: str) -> str | None:
    return _run_command(["/usr/sbin/sysctl", "-n", name])


def host_metadata() -> dict[str, Any]:
    commit = _run_command(["git", "rev-parse", "HEAD"])
    dirty = _run_command(["git", "status", "--porcelain"])
    metadata: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "git_commit": commit,
        "git_dirty": bool(dirty) if dirty is not None else None,
        "cpu_count": os.cpu_count(),
    }
    if platform.system() == "Darwin":
        metadata.update({
            "hardware_model": _sysctl("hw.model"),
            "chip": _sysctl("machdep.cpu.brand_string"),
            "physical_memory_bytes": _integer_or_none(_sysctl("hw.memsize")),
        })
    return metadata


def _integer_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _json_get(url: str, *, timeout: float) -> Any:
    with urlrequest.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def ollama_metadata(workload: Mapping[str, Any], *, timeout: float) -> dict[str, Any]:
    endpoint = str(workload["endpoint"]).rstrip("/")
    base = endpoint[:-9] if endpoint.endswith("/api/chat") else endpoint
    model = str(workload["model"])
    metadata: dict[str, Any] = {
        "endpoint": endpoint,
        "model": model,
        "client_environment": {
            key: os.environ[key]
            for key in OLLAMA_ENV_ALLOWLIST
            if key in os.environ
        },
    }
    for name, suffix in (("version", "/api/version"), ("loaded_models", "/api/ps")):
        try:
            metadata[name] = _json_get(base + suffix, timeout=timeout)
        except (OSError, ValueError) as exc:
            metadata[name] = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        tags = _json_get(base + "/api/tags", timeout=timeout)
        matches = [
            item for item in tags.get("models", [])
            if item.get("name") == model or item.get("model") == model
        ]
        metadata["model_inventory"] = matches
    except (OSError, ValueError) as exc:
        metadata["model_inventory"] = {"error": f"{type(exc).__name__}: {exc}"}
    return metadata


def _parse_vm_stat(text: str) -> dict[str, int]:
    first = text.splitlines()[0] if text else ""
    match = re.search(r"page size of (\d+) bytes", first)
    page_size = int(match.group(1)) if match else 4096
    result = {"page_size_bytes": page_size}
    for line in text.splitlines()[1:]:
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        digits = re.sub(r"[^0-9]", "", raw)
        if digits:
            result[key.strip().lower().replace(" ", "_")] = int(digits)
    return result


def _darwin_memory() -> dict[str, Any]:
    vm_text = _run_command(["/usr/bin/vm_stat"])
    pages = _parse_vm_stat(vm_text or "")
    page_size = pages.get("page_size_bytes", 4096)
    swap_text = _sysctl("vm.swapusage") or ""
    swap = re.search(r"used = ([0-9.]+)([MG])", swap_text)
    swap_used = None
    if swap:
        multiplier = 1024 ** (2 if swap.group(2) == "M" else 3)
        swap_used = int(float(swap.group(1)) * multiplier)
    return {
        "vm_pages": pages,
        "active_bytes": pages.get("pages_active", 0) * page_size,
        "wired_bytes": pages.get("pages_wired_down", 0) * page_size,
        "compressed_bytes": pages.get("pages_occupied_by_compressor", 0) * page_size,
        "swap_used_bytes": swap_used,
    }


def _linux_memory() -> dict[str, Any]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return {
        "memory_total_bytes": values.get("MemTotal"),
        "memory_available_bytes": values.get("MemAvailable"),
        "swap_used_bytes": (
            values.get("SwapTotal", 0) - values.get("SwapFree", 0)
            if values else None
        ),
    }


def _ollama_rss_bytes() -> int | None:
    table = _run_command(["/bin/ps", "-axo", "pid=,rss=,command="])
    if table is None:
        return None
    total_kib = 0
    matched = False
    for line in table.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) != 3:
            continue
        _, rss, command = parts
        lowered = command.lower()
        if "ollama" not in lowered or "parallel_benchmark" in lowered:
            continue
        try:
            total_kib += int(rss)
            matched = True
        except ValueError:
            continue
    return total_kib * 1024 if matched else None


def memory_snapshot(offset_seconds: float) -> dict[str, Any]:
    memory = _darwin_memory() if platform.system() == "Darwin" else _linux_memory()
    memory.update({
        "offset_seconds": round(offset_seconds, 6),
        "ollama_process_rss_bytes": _ollama_rss_bytes(),
    })
    return memory


class MemorySampler:
    def __init__(self, interval_seconds: float):
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, Any]] = []
        self.started = 0.0
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.thread.start()

    def _sample(self) -> None:
        while not self.stop_event.is_set():
            self.samples.append(memory_snapshot(time.monotonic() - self.started))
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> list[dict[str, Any]]:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(2.0, self.interval_seconds * 2))
        self.samples.append(memory_snapshot(time.monotonic() - self.started))
        return self.samples


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "p95": None, "max": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "n": len(ordered),
        "min": min(ordered),
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "p95": ordered[p95_index],
        "max": max(ordered),
    }


def _synthetic_request(workload: Mapping[str, Any], request_index: int) -> dict[str, Any]:
    delay = float(workload["delays_seconds"][request_index % len(workload["delays_seconds"])])
    started = time.monotonic()
    time.sleep(delay)
    return {
        "latency_seconds": time.monotonic() - started,
        "attempts": 1,
        "retries": 0,
        "success": True,
        "prompt_tokens": int(workload.get("prompt_tokens", 1)),
        "generated_tokens": int(workload.get("generated_tokens", 1)),
        "server": {},
        "response_sha256": hashlib.sha256(f"synthetic-{request_index}".encode()).hexdigest(),
        "error": None,
    }


def _ollama_request(
    workload: Mapping[str, Any],
    *,
    request_index: int,
    seed: int,
    timeout: float,
    max_retries: int,
) -> dict[str, Any]:
    prompt = workload["prompts"][request_index % len(workload["prompts"])]
    payload: dict[str, Any] = {
        "model": workload["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": bool(workload.get("think", False)),
        "keep_alive": workload.get("keep_alive", "10m"),
        "options": {
            "seed": seed,
            "temperature": float(workload.get("temperature", 0)),
            "num_predict": int(workload["num_predict"]),
        },
    }
    if workload.get("format") is not None:
        payload["format"] = workload["format"]
    encoded = canonical_json(payload).encode("utf-8")
    started = time.monotonic()
    failures: list[str] = []
    for attempt in range(max_retries + 1):
        try:
            req = urlrequest.Request(
                str(workload["endpoint"]),
                data=encoded,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read())
            content = str(body.get("message", {}).get("content", ""))
            return {
                "latency_seconds": time.monotonic() - started,
                "attempts": attempt + 1,
                "retries": attempt,
                "success": bool(body.get("done")),
                "prompt_tokens": int(body.get("prompt_eval_count", 0)),
                "generated_tokens": int(body.get("eval_count", 0)),
                "server": {
                    key: body.get(key)
                    for key in (
                        "done_reason",
                        "total_duration",
                        "load_duration",
                        "prompt_eval_duration",
                        "eval_duration",
                    )
                },
                "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "response_characters": len(content),
                "error": None if body.get("done") else "response did not set done=true",
            }
        except (urlerror.URLError, TimeoutError, ValueError, OSError) as exc:
            failures.append(f"{type(exc).__name__}: {exc}")
            if attempt < max_retries:
                time.sleep(min(1.0, 0.1 * (2 ** attempt)))
    return {
        "latency_seconds": time.monotonic() - started,
        "attempts": max_retries + 1,
        "retries": max_retries,
        "success": False,
        "prompt_tokens": 0,
        "generated_tokens": 0,
        "server": {},
        "response_sha256": None,
        "error": failures[-1] if failures else "unknown request failure",
    }


def _logical_run(
    protocol: Mapping[str, Any],
    *,
    run_index: int,
    repetition: int,
) -> dict[str, Any]:
    workload = protocol["workload"]
    started = time.monotonic()
    requests = []
    for request_index in range(int(protocol["requests_per_run"])):
        global_index = run_index * int(protocol["requests_per_run"]) + request_index
        if workload["kind"] == "synthetic":
            result = _synthetic_request(workload, global_index)
        else:
            result = _ollama_request(
                workload,
                request_index=global_index,
                seed=int(protocol.get("seed", 20261027)) + repetition * 10_000 + global_index,
                timeout=float(protocol["request_timeout_seconds"]),
                max_retries=int(protocol["max_retries"]),
            )
        result["request_index"] = request_index
        requests.append(result)
    return {
        "run_index": run_index,
        "latency_seconds": time.monotonic() - started,
        "success": all(item["success"] for item in requests),
        "requests": requests,
    }


def _memory_summary(samples: list[Mapping[str, Any]]) -> dict[str, Any]:
    def numeric(key: str) -> list[int]:
        return [int(item[key]) for item in samples if item.get(key) is not None]

    result: dict[str, Any] = {"sample_count": len(samples)}
    for key in (
        "active_bytes",
        "wired_bytes",
        "compressed_bytes",
        "memory_available_bytes",
        "swap_used_bytes",
        "ollama_process_rss_bytes",
    ):
        values = numeric(key)
        if values:
            result[key] = {
                "start": values[0],
                "end": values[-1],
                "min": min(values),
                "max": max(values),
                "delta": values[-1] - values[0],
            }
    return result


def run_trial(protocol: Mapping[str, Any], *, workers: int, repetition: int) -> dict[str, Any]:
    sampler = MemorySampler(float(protocol["sample_interval_seconds"]))
    sampler.start()
    started = time.monotonic()
    runs = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_logical_run, protocol, run_index=index, repetition=repetition)
            for index in range(int(protocol["logical_runs"]))
        ]
        for future in as_completed(futures):
            runs.append(future.result())
    makespan = time.monotonic() - started
    samples = sampler.stop()
    runs.sort(key=lambda item: item["run_index"])
    requests = [request for run in runs for request in run["requests"]]
    generated = sum(item["generated_tokens"] for item in requests if item["success"])
    prompt = sum(item["prompt_tokens"] for item in requests if item["success"])
    successful_requests = sum(bool(item["success"]) for item in requests)
    return {
        "repetition": repetition,
        "workers": workers,
        "makespan_seconds": makespan,
        "logical_runs": {
            "total": len(runs),
            "successful": sum(bool(run["success"]) for run in runs),
            "failed": sum(not run["success"] for run in runs),
        },
        "requests": {
            "total": len(requests),
            "successful": successful_requests,
            "failed": len(requests) - successful_requests,
            "retries": sum(item["retries"] for item in requests),
        },
        "tokens": {"prompt": prompt, "generated": generated, "total": prompt + generated},
        "throughput": {
            "requests_per_second": successful_requests / makespan if makespan else None,
            "generated_tokens_per_second": generated / makespan if makespan else None,
            "total_tokens_per_second": (prompt + generated) / makespan if makespan else None,
        },
        "run_latency_seconds": _summary([run["latency_seconds"] for run in runs]),
        "request_latency_seconds": _summary([item["latency_seconds"] for item in requests]),
        "memory": _memory_summary(samples),
        "memory_samples": samples,
        "runs": runs,
    }


def _aggregate_trials(workers: int, trials: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "workers": workers,
        "repetitions": len(trials),
        "makespan_seconds": _summary([float(item["makespan_seconds"]) for item in trials]),
        "generated_tokens_per_second": _summary([
            float(item["throughput"]["generated_tokens_per_second"])
            for item in trials
            if item["throughput"]["generated_tokens_per_second"] is not None
        ]),
        "request_latency_seconds": _summary([
            float(item["request_latency_seconds"]["mean"])
            for item in trials
            if item["request_latency_seconds"]["mean"] is not None
        ]),
        "failed_requests": sum(int(item["requests"]["failed"]) for item in trials),
        "retries": sum(int(item["requests"]["retries"]) for item in trials),
    }


def _observations(aggregates: list[Mapping[str, Any]]) -> dict[str, Any]:
    zero_error = [item for item in aggregates if item["failed_requests"] == 0]
    fastest = min(
        zero_error,
        key=lambda item: float(item["makespan_seconds"]["mean"]),
        default=None,
    )
    baseline = next((item for item in aggregates if item["workers"] == 1), None)
    scaling = []
    if baseline and baseline["makespan_seconds"]["mean"] is not None:
        baseline_mean = float(baseline["makespan_seconds"]["mean"])
        baseline_latency = float(baseline["request_latency_seconds"]["mean"])
        baseline_throughput = float(
            baseline["generated_tokens_per_second"]["mean"]
        )
        for item in aggregates:
            mean = item["makespan_seconds"]["mean"]
            if mean is None:
                continue
            speedup = baseline_mean / float(mean)
            scaling.append({
                "workers": item["workers"],
                "speedup_vs_workers_1": speedup,
                "parallel_efficiency": speedup / int(item["workers"]),
                "request_latency_multiplier_vs_workers_1": (
                    float(item["request_latency_seconds"]["mean"])
                    / baseline_latency
                    if baseline_latency else None
                ),
                "generated_token_throughput_multiplier_vs_workers_1": (
                    float(item["generated_tokens_per_second"]["mean"])
                    / baseline_throughput
                    if baseline_throughput else None
                ),
            })
    return {
        "fastest_zero_request_error_worker_count": fastest["workers"] if fastest else None,
        "scaling": scaling,
        "interpretation_boundary": (
            "Engineering observations only. This microbenchmark does not rank science "
            "systems and does not by itself authorize a long campaign."
        ),
    }


def execute(protocol: Mapping[str, Any]) -> dict[str, Any]:
    started_utc = utc_now()
    workload = protocol["workload"]
    backend = (
        ollama_metadata(workload, timeout=float(protocol["request_timeout_seconds"]))
        if workload["kind"] == "ollama_chat"
        else {"kind": "synthetic"}
    )
    warmup = []
    if workload["kind"] == "ollama_chat":
        for request_index in range(int(protocol.get("warmup_requests", 0))):
            result = _ollama_request(
                workload,
                request_index=request_index,
                seed=int(protocol.get("seed", 20261027)) - 1 - request_index,
                timeout=float(protocol["request_timeout_seconds"]),
                max_retries=int(protocol["max_retries"]),
            )
            warmup.append(result)
            if not result["success"]:
                raise RuntimeError(f"Ollama warmup failed: {result['error']}")
    trials = []
    for repetition in range(int(protocol["repetitions"])):
        offset = repetition % len(protocol["worker_counts"])
        order = protocol["worker_counts"][offset:] + protocol["worker_counts"][:offset]
        for workers in order:
            trials.append(run_trial(protocol, workers=int(workers), repetition=repetition))
        cooldown = float(protocol.get("cooldown_seconds", 0))
        if cooldown > 0 and repetition + 1 < int(protocol["repetitions"]):
            time.sleep(cooldown)
    aggregates = [
        _aggregate_trials(
            int(workers),
            [item for item in trials if item["workers"] == workers],
        )
        for workers in protocol["worker_counts"]
    ]
    return {
        "schema": REPORT_SCHEMA,
        "protocol_id": protocol["id"],
        "protocol_sha256": sha256(protocol),
        "started_utc": started_utc,
        "finished_utc": utc_now(),
        "host": host_metadata(),
        "backend": backend,
        "warmup": warmup,
        "protocol": protocol,
        "trials": trials,
        "aggregates": aggregates,
        "observations": _observations(aggregates),
    }


def markdown_report(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Parallel benchmark: {report['protocol_id']}",
        "",
        f"- Started: `{report['started_utc']}`",
        f"- Finished: `{report['finished_utc']}`",
        f"- Protocol SHA-256: `{report['protocol_sha256']}`",
        f"- Workload: `{report['protocol']['workload']['kind']}`",
        f"- Git commit: `{report['host'].get('git_commit')}`",
        "",
        "| workers | mean makespan (s) | speedup | efficiency | generated tok/s | mean request latency (s) | latency multiplier | failed requests | retries |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    scaling = {item["workers"]: item for item in report["observations"]["scaling"]}
    for item in report["aggregates"]:
        relative = scaling.get(item["workers"], {})
        lines.append(
            "| {workers} | {makespan:.3f} | {speedup:.3f} | {efficiency:.3f} | "
            "{tokens:.3f} | {latency:.3f} | {latency_multiplier:.3f} | "
            "{failed} | {retries} |".format(
                workers=item["workers"],
                makespan=item["makespan_seconds"]["mean"] or 0,
                speedup=relative.get("speedup_vs_workers_1", 0),
                efficiency=relative.get("parallel_efficiency", 0),
                tokens=item["generated_tokens_per_second"]["mean"] or 0,
                latency=item["request_latency_seconds"]["mean"] or 0,
                latency_multiplier=relative.get(
                    "request_latency_multiplier_vs_workers_1", 0
                ),
                failed=item["failed_requests"],
                retries=item["retries"],
            )
        )
    fastest = report["observations"]["fastest_zero_request_error_worker_count"]
    lines.extend([
        "",
        "## Observations",
        "",
        f"Fastest tested zero-request-error configuration: `{fastest}` workers.",
        "This is a measured engineering observation, not an automatic adoption gate.",
        "A representative harness smoke trial and output-integrity comparison are still",
        "required before committing a long optimization campaign.",
        "",
        report["observations"]["interpretation_boundary"],
        "",
    ])
    return "\n".join(lines)


def execution_plan(protocol: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": protocol["id"],
        "protocol_sha256": sha256(protocol),
        "worker_counts": protocol["worker_counts"],
        "repetitions": protocol["repetitions"],
        "logical_runs_per_trial": protocol["logical_runs"],
        "requests_per_run": protocol["requests_per_run"],
        "total_requests": (
            len(protocol["worker_counts"])
            * int(protocol["repetitions"])
            * int(protocol["logical_runs"])
            * int(protocol["requests_per_run"])
        ),
        "warmup_requests": int(protocol.get("warmup_requests", 0)),
        "workload_kind": protocol["workload"]["kind"],
    }


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    protocol = load_protocol(args.protocol)
    if args.dry_run:
        print(json.dumps(execution_plan(protocol), indent=2, sort_keys=True))
        return 0
    if args.json_output is None or args.markdown_output is None:
        parser.error("--json-output and --markdown-output are required unless --dry-run")
    report = execute(protocol)
    _atomic_write(args.json_output, json.dumps(report, indent=2, sort_keys=True) + "\n")
    _atomic_write(args.markdown_output, markdown_report(report))
    print(json.dumps({
        "json_output": str(args.json_output),
        "markdown_output": str(args.markdown_output),
        "observations": report["observations"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
