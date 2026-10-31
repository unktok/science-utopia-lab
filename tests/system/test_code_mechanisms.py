from copy import deepcopy
import shutil
import subprocess

import pytest

from utopia.system.code_mechanisms import (CODE_SCHEMA, CodeExecutionError, DockerCodeExecutor,
    validate_code_artifact, validate_code_result)
from utopia.optimization.code_lab import INPUT_SCHEMAS, REQUIRED_OUTPUTS, run_code_lab


def artifact(source="def step(context):\n    return {'outputs': {'out': []}, 'state': {'calls': 1}}"):
    return {"schema": CODE_SCHEMA, "label": "Test algorithm", "source": source,
            "inputs": {}, "outputs": {"out": {"type": "object"}},
            "state_schema": {"type": "object", "required": ["calls"],
                             "properties": {"calls": {"type": "integer"}}}}


def context():
    return {"inputs": {}, "state": {}, "random_seed": 4, "period": 0, "parameters": {}}


@pytest.fixture(scope="module")
def executor():
    if not shutil.which("docker"):
        pytest.skip("Docker unavailable")
    try:
        return DockerCodeExecutor()
    except (CodeExecutionError, subprocess.SubprocessError):
        pytest.skip("local container image/daemon unavailable")


def test_arbitrary_python_algorithm_is_not_ast_dsl():
    validate_code_artifact(artifact("""import math
def helper(values):
    return sorted({int(math.sqrt(x*x)) for x in values if x > 0})
def step(context):
    return {'outputs': {'out': [{'payload': {'values': helper([3,-2,1,3])}}]},
            'state': {'calls': 1}}
"""))


@pytest.mark.parametrize("source", ["def other(c): pass", "async def step(c): pass",
                                     "def step(c, other): pass", "def step(*args): pass"])
def test_entry_contract(source):
    with pytest.raises(ValueError):
        validate_code_artifact(artifact(source))


def test_reject_remote_schema_resolution():
    value = artifact()
    value["outputs"]["out"]["$defs"] = {"unused": {"$ref": "https://example.org/secret"}}
    with pytest.raises(ValueError, match="references"):
        validate_code_artifact(value)


def test_reject_host_regex_evaluation():
    value = artifact()
    value["outputs"]["out"] = {"type": "object", "properties": {
        "text": {"type": "string", "pattern": "(a+)+$"}}}
    with pytest.raises(ValueError, match="regexes"):
        validate_code_artifact(value)


@pytest.mark.parametrize("result", [
    {"outputs": {"undeclared": []}, "state": {"calls": 1}},
    {"outputs": {"out": []}, "state": {}},
    {"outputs": {"out": [{"payload": {}, "loss": -999}]}, "state": {"calls": 1}},
    {"outputs": {"out": [{"payload": {"x": float('nan')}}]}, "state": {"calls": 1}},
    {"outputs": {"out": [{"payload": {}, "actor_ids": "person"}]}, "state": {"calls": 1}},
])
def test_bad_results_are_technical_failures(result):
    with pytest.raises(CodeExecutionError):
        validate_code_result(artifact(), result)


def test_container_algorithm_and_receipt(executor):
    value = artifact("""import math
def step(context):
    values = sorted({int(math.sqrt(x*x)) for x in [3,-2,1,3] if x > 0})
    return {'outputs': {'out': [{'payload': {'values': values}}]}, 'state': {'calls': 1}}
""")
    run = executor.execute(value, context())
    assert run.result["outputs"]["out"][0]["payload"]["values"] == [1, 3]
    assert run.receipt["image_id"] == executor.image_id
    assert run.receipt["result_sha256"] == executor.execute(value, context()).receipt["result_sha256"]


def test_no_network_or_host_mount_and_readonly_root(executor):
    value = artifact("""import os, socket
def step(context):
    result = {'host_mounted': os.path.exists('/Users/shiro'),
              'docker_socket': os.path.exists('/var/run/docker.sock'),
              'uid': os.getuid()}
    try:
        open('/should-not-write', 'w').write('no')
        result['root_writable'] = True
    except OSError:
        result['root_writable'] = False
    try:
        socket.create_connection(('1.1.1.1', 443), timeout=0.2)
        result['network'] = True
    except OSError:
        result['network'] = False
    return {'outputs': {'out': [{'payload': result}]}, 'state': {'calls': 1}}
""")
    payload = executor.execute(value, context()).result["outputs"]["out"][0]["payload"]
    assert payload == {'host_mounted': False, 'docker_socket': False, 'uid': 65534,
                       'root_writable': False, 'network': False}


def test_runtime_failure_never_falls_back(executor):
    with pytest.raises(CodeExecutionError, match="ZeroDivisionError"):
        executor.execute(artifact("def step(c):\n    return 1/0"), context())


def test_container_timeout_cleanup(executor):
    short = DockerCodeExecutor(executor.image_id, timeout=1)
    with pytest.raises(CodeExecutionError, match="wall-time"):
        short.execute(artifact("import time\ndef step(c):\n    time.sleep(10)"), context())


def test_raw_output_flood_is_bounded(executor):
    with pytest.raises(CodeExecutionError, match="output byte"):
        executor.execute(artifact("import os\ndef step(c):\n    while True: os.write(1, b'x'*65536)"), context())


def production_artifact():
    value = artifact("""def step(context):
    outputs = {'decisions': [], 'replication_tasks': []}
    state = dict(context['state'])
    state['seen'] = list(state.get('seen', []))
    for delivered in context['inputs']['review_batches']:
        batch = delivered['payload']
        for paper in batch['papers']:
            scores = [r['overall_score'] for r in batch['reviews'][paper['id']]]
            decision = 'accept' if max(scores) >= 4 else 'reject'
            outputs['decisions'].append({'payload': {'batch_id': batch['batch_id'],
                'paper_id': paper['id'], 'paper': paper, 'decision': decision},
                'actor_ids': [paper['author_id']], 'artifact_ids': [paper['id']]})
            outputs['replication_tasks'].append({'payload': {'paper_id': paper['id'], 'priority': max(scores)}})
            state['seen'].append(paper['id'])
    return {'outputs': outputs, 'state': state}
""")
    value["inputs"] = deepcopy(INPUT_SCHEMAS)
    value["outputs"] = {**REQUIRED_OUTPUTS, "replication_tasks": {
        "type": "object", "required": ["paper_id", "priority"],
        "properties": {"paper_id": {"type": "string"}, "priority": {"type": "number"}}}}
    value["state_schema"] = {"type": "object", "required": ["seen"], "properties": {
        "seen": {"type": "array", "items": {"type": "string"}}}}
    return value


def test_graph_production_records_new_artifacts_and_checkpoint(executor):
    value = production_artifact()
    full = run_code_lab(value, executor)
    assert full["summary"] == {"accepted": 4, "rejected": 1, "publication_records": 5,
                               "invented_artifacts": 5, "blocked_invocations": 0}
    first = run_code_lab(value, executor, periods=1)
    resumed = run_code_lab(value, executor, periods=1, checkpoint=first["checkpoint"])
    assert resumed["checkpoint"] == full["checkpoint"]
    assert first["events"] + resumed["events"] == full["events"]
