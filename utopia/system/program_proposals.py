"""Optional local Qwen proposals, parsed as data and bound to model receipts."""
from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

import requests

from utopia.optimization.generative_system import program_node, validate_generative_system
from utopia.system import ChannelKind, ConnectionSpec, MechanismFamily, ScheduleSpec, SystemSpec
from utopia.system.program_world import WORLD_SCHEMA, validate_world
from utopia.system.programs import digest, validate_program


def generate_local_proposal(
    *, model: str = "qwen3:8b", endpoint: str = "http://localhost:11434",
    seed: int = 811, population: int = 6,
) -> dict[str, Any]:
    """Ask a local LLM for a new executable rule and initial agent attributes.

    LLM text generation is outside autograd. The resulting versioned numeric
    world and rule are frozen inputs to subsequent simulator optimization.
    There is no fallback to a fixture when generation or validation fails.
    """
    if endpoint not in {"http://localhost:11434", "http://127.0.0.1:11434"}:
        raise ValueError("v1 local proposal adapter accepts the default loopback Ollama endpoint")
    if isinstance(population, bool) or not isinstance(population, int) or not 2 <= population <= 10:
        raise ValueError("population must be in [2,10]")
    tags = requests.get(endpoint + "/api/tags", timeout=10)
    tags.raise_for_status()
    models = {item["name"]: item["digest"] for item in tags.json()["models"]}
    if model not in models:
        raise ValueError(f"local model {model!r} is not installed")
    prompt = f"""Design one new science-ecosystem mechanism, such as replication
commons, mentoring, shared instrumentation or scientific memory. Invent its
numeric rule; do not just name an existing funding or review rule.
Return ONLY a JSON object with exactly these fields:
label: short mechanism name
rationale: one sentence explaining the rule
effects: an object mapping one or two of allocation, access, learning, effort
to numeric strengths between -2 and 2
world: an object with quality, novelty, resources, knowledge, each an array of
exactly {population} numbers in [0,1] describing distinct initial researchers
program: an executable AST object with EXACT keys:
  schema: "scienceutopia.mechanism-program.v1"
  inputs: {{"quality":"vector","novelty":"vector","resources":"vector",
           "knowledge":"vector","signal":"vector"}}
  parameters: {{"gain":{{"initial":0.7,"minimum":-2,"maximum":2}},
                "bias":{{"initial":-0.1,"minimum":-2,"maximum":2}}}}
  state: {{"memory":0.0}}
  output: an expression AST (see below)
  updates: {{"memory": an expression AST}}
Expression forms are ONLY {{"input":"quality"}} (or another declared input),
{{"state":"memory"}}, {{"param":"gain"}}, {{"param":"bias"}}, {{"const":0.3}},
or {{"op":"add","args":[expression,expression]}}.
Operators: add/sub/mul/threshold take 2 args; sigmoid/tanh/mean/square take 1.
threshold(a,b) means a>=b in discrete execution, sigmoid((a-b)/0.25) when relaxed.
Keep each expression depth <=5. Output and state updates are bounded by tanh.
Use both the incoming signal and at least one researcher attribute in output.
Use memory in its update and use at least one parameter in output.
Do not include source code, markdown, or undeclared operators or names.
"""
    attempts = []
    for attempt in range(2):
        messages = [{"role": "user", "content": prompt}]
        if attempts:
            messages.append({"role": "user", "content": (
                "The prior response was invalid: " + attempts[-1]["error"]
                + ". Produce a fresh complete valid JSON object."
            )})
        body = {
            "model": model, "messages": messages, "stream": False,
            "think": False, "format": "json", "keep_alive": "5m",
            "options": {"temperature": 0.0, "seed": seed + attempt,
                        "num_predict": 2000, "num_ctx": 6144},
        }
        response = requests.post(endpoint + "/api/chat", json=body, timeout=(10, 180))
        response.raise_for_status()
        result = response.json()
        text = result["message"]["content"]
        receipt = {
            "request_sha256": digest(body), "response_sha256": digest(result),
            "model": model, "model_digest": models[model],
            "total_duration_ns": result.get("total_duration"),
            "prompt_eval_count": result.get("prompt_eval_count"),
            "eval_count": result.get("eval_count"),
        }
        try:
            proposal = json.loads(text)
            if set(proposal) != {"label", "rationale", "effects", "world", "program"}:
                raise ValueError("proposal fields mismatch")
            if not isinstance(proposal["label"], str) or not 1 <= len(proposal["label"]) <= 120:
                raise ValueError("invalid mechanism label")
            if not isinstance(proposal["rationale"], str):
                raise ValueError("rationale must be a string")
            validate_program(proposal["program"])
            world = {
                **proposal["world"], "schema": WORLD_SCHEMA,
                "population": population, "seed": seed,
                "source": {"kind": "local-qwen-generated-attributes", "receipt": receipt},
            }
            validate_world(world)
            node = program_node("generated-commons", MechanismFamily.CUSTOM,
                                proposal["program"], proposal["effects"], label=proposal["label"])
            validate_generative_system(SystemSpec(
                "generated-proposal-check", 1, mechanisms=(node,),
                schedules=(ScheduleSpec(node.mechanism_id, 0),),
            ))
            return {"proposal": proposal, "world": world, "receipt": receipt,
                    "attempts": attempts, "response": result}
        except (ValueError, TypeError, KeyError) as error:
            attempts.append({"receipt": receipt, "error": str(error), "response": result})
    raise ValueError("local proposal failed validation twice: " + json.dumps(attempts))


def attach_generated_proposal(system: SystemSpec, generated: dict[str, Any]) -> SystemSpec:
    proposal = generated["proposal"]
    name = "generated-commons"
    node = program_node(name, MechanismFamily.CUSTOM, proposal["program"],
                        proposal["effects"], label=proposal["label"])
    if name in {item.mechanism_id for item in system.mechanisms}:
        raise ValueError("generated node already attached")
    # Two explicit edges make the invented rule part of the research process.
    source = system.mechanisms[0].mechanism_id
    target = system.mechanisms[-1].mechanism_id
    spec = replace(
        system, mechanisms=(*system.mechanisms, node),
        connections=(*system.connections,
                     ConnectionSpec(source, "out", name, "in", ChannelKind.SIGNAL, latency=1),
                     ConnectionSpec(name, "out", target, "in", ChannelKind.SIGNAL)),
        schedules=(*system.schedules, ScheduleSpec(name, len(system.schedules))),
    )
    validate_generative_system(spec)
    return spec
