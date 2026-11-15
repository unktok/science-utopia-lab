"""Pure retained-graph construction; no authored-code or native-world execution."""
import ast
import json
from pathlib import Path

import pytest

from utopia.optimization.native_workflow_domain_v4 import (
    post_funding_cost_control, require_workflow_candidate)
from utopia.system import SystemSpec
from utopia.system.native_kernel import CONTEXT_RECEIVER
from utopia.system.native_legacy_choice_controls import controls, PRODUCER, RECEIVER, SOURCE

ROOT = Path(__file__).resolve().parents[2]


def anchor():
    report = json.loads((ROOT / 'research/data/native-longitudinal-development-v1/scores/report.json').read_text())
    return SystemSpec.from_dict(report['selection']['selected']['scalar::content-utility']['system'])


def test_three_literal_controls_preserve_original_world_and_caller_anchor():
    original = anchor(); post = post_funding_cost_control(original)
    before = post.to_dict(); result = controls(post)
    assert list(result) == ['core-assignment', 'native-choice', 'native-choice-advice']
    assert post.to_dict() == before and result['core-assignment'] is post
    for candidate in result.values():
        assert candidate.initial_state == original.initial_state
        assert require_workflow_candidate(original, candidate)
    cut = result['native-choice']
    assert cut.connections == post.connections and cut.schedules == post.schedules
    changed = [n.mechanism_id for n, old in zip(cut.mechanisms, post.mechanisms) if n != old]
    assert changed == ['developer-catalog-agenda']
    director = next(n for n in cut.mechanisms if n.mechanism_id == changed[0])
    assert director.parameters['actuation'] == 'cut'


def test_advice_has_actual_pre_research_context_wiring_not_direct_project_assignment():
    post = post_funding_cost_control(anchor()); result = controls(post)
    cut, advised = result['native-choice'], result['native-choice-advice']
    assert len(advised.mechanisms) == len(cut.mechanisms) + 2
    assert len(advised.connections) == len(cut.connections) + 2
    assert advised.mechanisms[:len(cut.mechanisms)] == cut.mechanisms
    node = next(n for n in advised.mechanisms if n.mechanism_id == PRODUCER)
    assert node.parameters['code_artifact']['source'] == SOURCE
    assert [p.port_id for p in node.outputs] == ['messages']
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(ast.parse(SOURCE)))
    phases = {s.mechanism_id: s.phase for s in advised.schedules}
    assert phases['world.open'] < phases[PRODUCER] < phases[RECEIVER] < phases['world.research']
    assert any(e.source_mechanism == PRODUCER and e.target_mechanism == RECEIVER
               and e.target_port == 'messages' for e in advised.connections)
    receiver = next(n for n in advised.mechanisms if n.mechanism_id == RECEIVER)
    assert receiver.implementation == CONTEXT_RECEIVER == 'native.world.researcher-context.v1'


def test_default_pre_funding_seed_is_not_silently_reordered():
    with pytest.raises(ValueError, match='post-funding'):
        controls(anchor())


def test_retained_native_construction_proof_is_not_a_real_model_gain_claim():
    import hashlib
    import subprocess
    from utopia.optimization.native_numeric_designer import checked
    receipt = checked(json.loads((ROOT / 'research/results/native-legacy-choice-construction-software-v1.json').read_text()))
    raw = (ROOT / receipt['verification_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt['verification_file_sha256']
    value = json.loads(raw)
    assert value['source_commit'] == receipt['source_commit']
    for name, sha in receipt['source_files'].items():
        old = subprocess.check_output(['git', 'show', receipt['source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(old).hexdigest() == sha
    assert receipt['software_worlds'] == 3 and receipt['annual_boundaries'] == 12
    assert sum(receipt['recorded_code_context_rows'].values()) == 76
    assert receipt['native_direction_requests'] == [0, 16, 16]
    assert receipt['advice_deliveries'] == [0, 0, 16]
    assert value['same_initial_physical_society_verified']
    assert not receipt['scientific_feasibility_or_improvement_claimed']
    assert not receipt['pilot_operator_runner_and_scientist900_profile_verified']
    assert not receipt['publication_ready'] and receipt['new_real_model_calls'] == 0
