"""Generated Python mechanisms behind a JSON contract and a container boundary.

No generated source is executed or imported in the research host process.
The contract is a compatibility/technical-validity boundary, not a policy veto.
Arbitrary Python on this route is black-box, not automatically differentiable.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import selectors
import shutil
import subprocess
import tempfile
import time
from typing import Any, Mapping
import uuid

from jsonschema import Draft202012Validator

from .runtime import (GraphRuntimeError, MechanismContext, MechanismEvent,
                      MechanismRegistry, MechanismResult, MechanismValue)


CODE_SCHEMA = "scienceutopia.code-mechanism.v1"
CODE_IMPLEMENTATION = "code.python.v1"
DEFAULT_IMAGE = "python:3.11-slim"
MAX_BYTES = 1_048_576


class CodeExecutionError(GraphRuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise ValueError("contract schema must be an object")
    if len(canonical(schema)) > 65_536:
        raise ValueError("contract schema exceeds size limit")
    def visit(item):
        if isinstance(item, dict):
            # No external or recursive resolution, including nested unused defs.
            if any(key in item for key in ("$ref", "$dynamicRef", "$recursiveRef")):
                raise ValueError("schema references are not supported")
            for value in item.values():
                visit(value)
        elif isinstance(item, list):
            for value in item:
                visit(value)
    visit(schema)
    Draft202012Validator.check_schema(schema)


def validate_code_artifact(artifact: Mapping[str, Any]) -> None:
    if not isinstance(artifact, dict) or set(artifact) != {
        "schema", "label", "source", "inputs", "outputs", "state_schema"
    } or artifact["schema"] != CODE_SCHEMA:
        raise ValueError("invalid code-mechanism artifact fields/schema")
    if not isinstance(artifact["label"], str) or not 1 <= len(artifact["label"]) <= 120:
        raise ValueError("label must be a nonempty string of at most 120 characters")
    source = artifact["source"]
    if not isinstance(source, str) or not 1 <= len(source.encode()) <= 65_536:
        raise ValueError("source must contain 1..65536 UTF-8 bytes")
    tree = ast.parse(source)
    entries = [item for item in tree.body
               if isinstance(item, ast.FunctionDef) and item.name == "step"]
    if len(entries) != 1:
        raise ValueError("source must define one top-level def step(context)")
    args = entries[0].args
    if (len(args.posonlyargs) + len(args.args) != 1 or args.vararg or args.kwarg
            or args.kwonlyargs or entries[0].decorator_list):
        raise ValueError("step must take exactly one positional argument without decorators")
    for direction in ("inputs", "outputs"):
        ports = artifact[direction]
        if not isinstance(ports, dict) or len(ports) > 32:
            raise ValueError("port schemas must be an object with at most 32 ports")
        for name, schema in ports.items():
            if not isinstance(name, str) or not name or len(name) > 120:
                raise ValueError("invalid port name")
            _schema(schema)
    _schema(artifact["state_schema"])
    if len(canonical(artifact)) > MAX_BYTES:
        raise ValueError("artifact exceeds size limit")


# This bootstrap is trusted; generated source and context arrive only on stdin.
# Python source is deliberately NOT restricted to an arithmetic/AST vocabulary.
_BOOTSTRAP = r'''
import contextlib, hashlib, json, os, random, resource, sys, traceback
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
request = json.loads(sys.stdin.buffer.read(1048577))
random.seed(request['context']['random_seed'])
namespace = {'__name__': 'generated_mechanism'}
try:
    with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
        exec(compile(request['source'], '<generated-mechanism>', 'exec'), namespace)
        result = namespace['step'](request['context'])
    encoded = json.dumps({'ok': True, 'result': result}, allow_nan=False, separators=(',', ':'))
except BaseException as error:
    encoded = json.dumps({'ok': False, 'error': traceback.format_exc(limit=5)[-4000:]})
sys.stdout.write(encoded)
'''


@dataclass(frozen=True)
class CodeExecution:
    result: dict[str, Any]
    receipt: dict[str, Any]


class DockerCodeExecutor:
    """Run each call in an ephemeral, no-network, no-host-mount container.

    This is defense in depth, not a claim that containers defeat kernel exploits.
    Source has full Python freedom *inside* its bounded container. Never mounts
    the repository, home, Docker socket, or credentials. No image is downloaded.
    """

    def __init__(self, image: str = DEFAULT_IMAGE, *, timeout: float = 15.0):
        if not 0.1 <= timeout <= 60:
            raise ValueError("timeout must be in [0.1,60] seconds")
        docker = shutil.which("docker")
        if not docker:
            raise CodeExecutionError("Docker is required; host execution is never a fallback")
        self.docker = docker
        self.timeout = timeout
        lookup = subprocess.run(
            [docker, "image", "inspect", image, "--format", "{{.Id}}"],
            text=True, capture_output=True, timeout=10,
        )
        self.image_id = lookup.stdout.strip()
        if lookup.returncode or not self.image_id.startswith("sha256:"):
            raise CodeExecutionError("a local Python container image is required: " + lookup.stderr[:500])

    def execute(self, artifact: dict[str, Any], context: dict[str, Any]) -> CodeExecution:
        validate_code_artifact(artifact)
        validate_context(artifact, context)
        request = canonical({"source": artifact["source"], "context": context})
        if len(request) > MAX_BYTES:
            raise CodeExecutionError("request exceeds byte limit")
        name = "utopia-code-" + uuid.uuid4().hex
        command = [self.docker, "run", "--rm", "--pull=never", "--name", name,
                   "--network", "none", "--read-only", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "--pids-limit", "32",
                   "--memory", "256m", "--memory-swap", "256m", "--cpus", "1",
                   "--user", "65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                   "-i", self.image_id, "/usr/local/bin/python", "-I", "-S", "-B",
                   "-c", _BOOTSTRAP]
        start = time.monotonic()
        stdout, stderr = bytearray(), bytearray()
        process = None
        try:
            with tempfile.TemporaryFile() as data, selectors.DefaultSelector() as selector:
                data.write(request)
                data.seek(0)
                process = subprocess.Popen(command, stdin=data, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                selector.register(process.stdout, selectors.EVENT_READ, stdout)
                selector.register(process.stderr, selectors.EVENT_READ, stderr)
                while selector.get_map():
                    if time.monotonic() - start > self.timeout:
                        raise CodeExecutionError("container wall-time limit exceeded")
                    for key, _ in selector.select(timeout=0.05):
                        block = key.fileobj.read1(65_536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        key.data.extend(block)
                        if len(stdout) + len(stderr) > MAX_BYTES:
                            raise CodeExecutionError("container output byte limit exceeded")
                process.wait(timeout=max(0.01, self.timeout - (time.monotonic() - start)))
                if process.returncode:
                    raise CodeExecutionError(f"container exited {process.returncode}: "
                                             + stderr.decode(errors="replace")[:1000])
        finally:
            if process is not None:
                # The exact generated container is the only deletion target.
                subprocess.run([self.docker, "rm", "-f", name], capture_output=True, timeout=10)
                if process.poll() is None:
                    process.kill()
                process.wait()
                process.stdout.close()
                process.stderr.close()
        try:
            envelope = json.loads(stdout)
        except (ValueError, UnicodeError) as error:
            raise CodeExecutionError("container returned invalid JSON") from error
        if not isinstance(envelope, dict) or envelope.get("ok") is not True:
            detail = envelope.get("error", envelope) if isinstance(envelope, dict) else envelope
            raise CodeExecutionError("generated step failed: " + str(detail)[:2000])
        result = envelope.get("result")
        validate_code_result(artifact, result)
        return CodeExecution(result, {
            "image_id": self.image_id, "artifact_sha256": sha(artifact),
            "context_sha256": sha(context), "result_sha256": sha(result),
            "wall_seconds": time.monotonic() - start,
        })


def validate_context(artifact: dict[str, Any], context: dict[str, Any]) -> None:
    if not isinstance(context, dict) or not isinstance(context.get("state"), dict):
        raise ValueError("context requires object state")
    if not isinstance(context.get("inputs"), dict) or set(context["inputs"]) != set(artifact["inputs"]):
        raise ValueError("context input ports do not match artifact")
    if isinstance(context.get("random_seed"), bool) or not isinstance(context.get("random_seed"), int):
        raise ValueError("context requires an integer random_seed")
    # Empty state is the universal first-call state; later states obey the schema.
    if context["state"]:
        Draft202012Validator(artifact["state_schema"]).validate(context["state"])
    for port, values in context["inputs"].items():
        if not isinstance(values, list):
            raise ValueError("inputs must be lists of delivered records")
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("payload"), dict):
                raise ValueError("each input record must contain object payload")
            Draft202012Validator(artifact["inputs"][port]).validate(value["payload"])
    canonical(context)


def validate_code_result(artifact: dict[str, Any], result: Any) -> None:
    if not isinstance(result, dict) or set(result) != {"outputs", "state"}:
        keys = list(result) if isinstance(result, dict) else type(result).__name__
        raise CodeExecutionError("step return keys are " + str(keys)
            + "; expected ONLY outputs and state. Every port, including new artifact ports,"
              " belongs inside outputs. Schema definitions belong only in manifest metadata.")
    if not isinstance(result["state"], dict) or not isinstance(result["outputs"], dict):
        raise CodeExecutionError("outputs and state must be objects")
    if set(result["outputs"]) != set(artifact["outputs"]):
        raise CodeExecutionError("step outputs must contain exactly ports " + str(list(artifact["outputs"]))
                                 + "; actual ports: " + str(list(result["outputs"])))
    try:
        Draft202012Validator(artifact["state_schema"]).validate(result["state"])
        for port, values in result["outputs"].items():
            if not isinstance(values, list) or len(values) > 1000:
                raise ValueError("each output must be a list of at most 1000 records")
            for value in values:
                if (not isinstance(value, dict) or not {"payload"} <= set(value)
                        or set(value) - {"payload", "actor_ids", "artifact_ids"}
                        or not isinstance(value["payload"], dict)):
                    raise ValueError(f"outputs[{port!r}] record must be {{'payload': object,"
                                     " optional actor_ids/artifact_ids}}; got " + str(value)[:1000])
                for field in ("actor_ids", "artifact_ids"):
                    ids = value.get(field, [])
                    if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
                        raise ValueError("record ids must be lists of nonempty strings")
                Draft202012Validator(artifact["outputs"][port]).validate(value["payload"])
        if len(canonical(result)) > MAX_BYTES:
            raise ValueError("result exceeds byte limit")
    except (ValueError, TypeError) as error:
        raise CodeExecutionError("invalid generated result: " + str(error)) from error
    except Exception as error:
        # JSON Schema violations are technical failures, never numeric penalties.
        raise CodeExecutionError("generated result violates its contract: " + str(error)[:2000]) from error


def register_code_mechanisms(registry: MechanismRegistry, executor: DockerCodeExecutor,
                             receipts: list[dict[str, Any]] | None = None) -> None:
    def handler(context: MechanismContext) -> MechanismResult:
        artifact = context.mechanism.parameters["code_artifact"]
        if (set(artifact["inputs"]) != {p.port_id for p in context.mechanism.inputs}
                or set(artifact["outputs"]) != {p.port_id for p in context.mechanism.outputs}):
            raise CodeExecutionError("SystemSpec ports and code contract do not agree")
        expected_image = context.mechanism.parameters.get("runtime_image_id")
        if expected_image != executor.image_id:
            raise CodeExecutionError("runtime image must match the SystemSpec pinned image id")
        # Common random numbers across candidate sources; changing code must not
        # silently change the exogenous seed for the same node and period.
        seed = int(sha({"period": context.period, "mechanism": context.mechanism.mechanism_id,
                        "seed": context.initial_state.get("seed", 0)})[:16], 16)
        request = {
            "period": context.period, "phase": context.phase, "random_seed": seed,
            "state": dict(context.state),
            "parameters": {k: v for k, v in context.mechanism.parameters.items()
                           if k not in {"code_artifact", "runtime_image_id"}},
            "inputs": {port.port_id: [
                {"payload": dict(value.payload), "actor_ids": list(value.actor_ids),
                 "artifact_ids": list(value.artifact_ids),
                 "source_mechanism": value.source_mechanism,
                 "emitted_period": value.emitted_period}
                for value in context.inputs.get(port.port_id, ())]
                for port in context.mechanism.inputs},
        }
        execution = executor.execute(artifact, request)
        if receipts is not None:
            receipts.append({"mechanism_id": context.mechanism.mechanism_id,
                             "period": context.period, **execution.receipt})
        return MechanismResult(
            outputs={port: tuple(MechanismValue(
                value["payload"], actor_ids=tuple(value.get("actor_ids", ())),
                artifact_ids=tuple(value.get("artifact_ids", ()))) for value in values)
                for port, values in execution.result["outputs"].items()},
            next_state=execution.result["state"],
            events=(MechanismEvent("generated.code_executed", payload={
                key: value for key, value in execution.receipt.items()
                if key != "wall_seconds"
            }),),
        )
    registry.register(CODE_IMPLEMENTATION, 1, handler)
