"""Result-conditioned local LLM source generation, with executable repair feedback."""
from __future__ import annotations

import json
from typing import Any, Callable

import requests

from .code_mechanisms import CODE_SCHEMA, sha, validate_code_artifact


def propose_local_code(
    *, task: str, input_schemas: dict[str, Any], required_outputs: dict[str, Any],
    history: list[dict[str, Any]], validate_executable: Callable[[dict], Any],
    model: str = "qwen3:8b", endpoint: str = "http://localhost:11434",
    seed: int = 911, max_attempts: int = 3,
    record_attempts: Callable[[list[dict]], None] | None = None,
) -> dict[str, Any]:
    """Generate actual source, not selection from a prewritten rule catalog.

    Compatibility ports are caller supplied. The model may invent additional
    output schemas and arbitrary JSON memory. Failed probes repair from actual
    error text. No fabricated valid artifact is substituted on failure.
    Caller must compute loss outside generated code/container.
    """
    if endpoint not in {"http://localhost:11434", "http://127.0.0.1:11434"}:
        raise ValueError("only the default loopback Ollama endpoint is supported")
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be in [1,5]")
    tags = requests.get(endpoint + "/api/tags", timeout=10)
    tags.raise_for_status()
    models = {item["name"]: item["digest"] for item in tags.json()["models"]}
    if model not in models:
        raise ValueError(f"local model {model!r} is not installed")
    prompt = """You implement a science-system institution as executable Python 3.11.
Return ONLY JSON with EXACT keys: label, rationale, source, additional_outputs, state_schema.
source is a JSON string of actual Python defining def step(context), not an AST.
You may use loops, conditionals, helpers, imports from the Python standard library,
sorting, dictionaries, lists, arbitrary JSON memory, and invent your own algorithm.
No external packages, network, files, or clock dependence. Use random only if needed:
the runner seeds it. Do not use hash() for randomness. All persistence is returned state.
context is a DICTIONARY, NOT a tuple: use context['period'], context['state'],
context['inputs']. Never unpack it as period, phase, ... = context.
Other keys are phase, random_seed, parameters. The first state is {}.
Each input port is a LIST of delivered records; access its
data as record['payload'], not record directly. Some lists may be empty.
For any input port: for record in context['inputs']['port_name']:
    payload = record['payload']
Never call .items() on a port's list.
Return EXACTLY {'outputs': {port_name: [record, ...], ...}, 'state': {...}}.
Every declared output port MUST appear, even if empty. Every output record is
{'payload': {...}, 'actor_ids': [string,...], 'artifact_ids': [string,...]}.
Never emit event_type, metrics, loss, or private host data. The host measures outcomes.
additional_outputs maps NEW output port names to JSON Schemas for their payloads.
Do not repeat required ports in additional_outputs. You may invent new information
artifacts rather than using only existing evaluation/funding categories.
state_schema is a JSON Schema matching the state your code returns. No $ref.
The required input and output payload schemas follow:
""" + json.dumps({"inputs": input_schemas, "required_outputs": required_outputs})
    prompt += "\nTASK:\n" + task + "\nPREVIOUS ACTUAL OBSERVATIONS:\n" + json.dumps(history)
    messages = [{"role": "user", "content": prompt}]
    attempts = []
    for index in range(max_attempts):
        body = {
            "model": model, "messages": messages, "stream": False,
            "think": False, "format": "json", "keep_alive": "5m",
            "options": {"temperature": 0.2, "seed": seed + index,
                        "num_predict": 3500, "num_ctx": 12288},
        }
        response = requests.post(endpoint + "/api/chat", json=body, timeout=(10, 240))
        response.raise_for_status()
        raw = response.json()
        text = raw["message"]["content"]
        receipt = {
            "request_sha256": sha(body), "response_sha256": sha(raw),
            "history_sha256": sha(history), "model": model,
            "model_digest": models[model], "eval_count": raw.get("eval_count"),
            "total_duration_ns": raw.get("total_duration"),
        }
        record = {"request": body, "response": raw, "receipt": receipt}
        attempts.append(record)
        try:
            proposal = json.loads(text)
            if not isinstance(proposal, dict) or set(proposal) != {
                "label", "rationale", "source", "additional_outputs", "state_schema"
            }:
                raise ValueError("proposal fields mismatch")
            additional = proposal["additional_outputs"]
            if not isinstance(additional, dict) or set(additional) & set(required_outputs):
                raise ValueError("additional_outputs must be new named payload schemas")
            artifact = {
                "schema": CODE_SCHEMA, "label": proposal["label"],
                "source": proposal["source"], "inputs": input_schemas,
                "outputs": {**required_outputs, **additional},
                "state_schema": proposal["state_schema"],
            }
            validate_code_artifact(artifact)
            evidence = validate_executable(artifact)
            record["status"] = "complete"
            if record_attempts:
                record_attempts(attempts)
            return {"artifact": artifact, "rationale": proposal["rationale"],
                    "receipt": receipt, "attempts": attempts, "evidence": evidence}
        except Exception as error:
            record["status"] = "invalid"
            record["error"] = str(error)[:4000]
            if record_attempts:
                record_attempts(attempts)
            messages = [*messages, {"role": "assistant", "content": text},
                        {"role": "user", "content": (
                            "Actual validation/execution failed: " + record["error"]
                            + "\nRepair the implementation and return a complete JSON proposal."
                        )}]
    raise ValueError("local executable proposal exhausted repairs: " + attempts[-1]["error"])
