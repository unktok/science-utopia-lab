"""Read-only followup audit contract tests, explicitly no Qwen evidence."""
from copy import deepcopy
import json

import pytest

from scripts import analyze_native_control_followup_v12 as audit
from scripts import run_native_control_followup_v12 as driver
from tests.optimization.test_native_control_followup_v12 import fixture_plan
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def fixture(root, *, failed=False):
    plan = fixture_plan()
    def factory(*args):
        if failed:
            raise RuntimeError('explicit-scripted-fixture-transport-failure')
        raise PortableStop('stop-before-first-scripted-native-world')
    try:
        driver.advance(root, plan, simulation_factory=factory, parent_guard=lambda: None)
    except PortableStop:
        pass
    driver.summarize(root, plan)
    return plan


def rewrite(root, mutation):
    path = root / 'evidence.json'
    raw = json.loads(path.read_text())
    mutation(raw)
    raw.pop('content_sha256')
    raw['content_sha256'] = digest(raw)
    write_json_atomic(path, raw, sort_keys=True, allow_nan=False)


@pytest.mark.parametrize('failed', [False, True])
def test_repeated_empty_or_failed_followup_is_byte_identical_read_only(tmp_path, failed):
    fixture(tmp_path, failed=failed)
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)
    second = audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)
    assert audit._inventory(tmp_path) == before
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first['status'] == ('technically-stopped' if failed else 'in-progress')
    assert first['loss_path'] == ([None] if failed else [])
    assert first['audit']['new_model_calls'] == first['audit']['new_container_executions'] == 0
    assert not first['claims']['post_final_cv_proposal_native_evaluated']
    with pytest.raises(ValueError, match='two completed'):
        audit.analyze(tmp_path, expected_source='followup-scripted-QA')


@pytest.mark.parametrize('tamper', ['source', 'worldseed', 'drawseed', 'update', 'causal', 'budget',
    'state', 'logq', 'counts', 'claims', 'failure-penalty'])
def test_rehashed_plan_state_or_claim_tampering_rejected(tmp_path, tamper):
    fixture(tmp_path, failed=tamper == 'failure-penalty')
    def change(raw):
        if tamper == 'source': raw['source_commit'] = 'forged'
        if tamper == 'counts': raw['physical_reply_count'] = 2
        if tamper == 'claims': raw['claims']['variance_reduction_established'] = True
        if tamper in ('worldseed', 'drawseed', 'update', 'causal', 'budget'):
            plan = deepcopy(raw['plan'])
            field, value = {'worldseed': ('world_seed', 43), 'drawseed': ('draw_seed', 42),
                'update': ('optimizer_update', True), 'causal': ('causal_comparison', True),
                'budget': ('planned_native_world_budget', 3)}[tamper]
            plan[field] = value
            raw['plan'] = plan
            write_json_atomic(tmp_path / 'plan.json', plan, sort_keys=True, allow_nan=False)
        if tamper in ('state', 'logq', 'failure-penalty'):
            state = deepcopy(raw['state'])
            if tamper == 'state': state['version_sha256'] = 'forged'
            if tamper == 'logq': state['draws'][0]['conditional_latent_log_probability'] += .1
            if tamper == 'failure-penalty': state['observations'][0]['loss'] = 999.
            raw['state'] = state
            write_json_atomic(tmp_path / 'state.json', state, sort_keys=True, allow_nan=False)
    rewrite(tmp_path, change)
    with pytest.raises(ValueError):
        audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)


def test_undeclared_world_and_symlinks_are_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'worlds/undeclared').mkdir(parents=True)
    with pytest.raises(ValueError, match='undeclared'):
        audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)


def test_actual_requires_explicit_parent_file_and_clean_historical_source(tmp_path):
    fixture(tmp_path)
    plan = json.loads((tmp_path / 'plan.json').read_text())
    plan.update(classification=driver.ACTUAL)
    plan['world'].update(source_commit='a'*40, classification=driver.ACTUAL)
    raw = json.loads((tmp_path / 'evidence.json').read_text())
    raw.update(source_commit='a'*40, classification=driver.ACTUAL, plan=plan)
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='explicit immutable parent'):
        audit._validate_plan(raw, plan, 'a'*40, parent_audit=None, parent_audit_source=None)


def test_concurrent_raw_mutation_fails_closed(tmp_path, monkeypatch):
    fixture(tmp_path)
    before = audit._inventory(tmp_path)
    calls = []
    def inventory(root):
        calls.append(1)
        return before if len(calls) == 1 else {**before, 'writer': 'changed'}
    monkeypatch.setattr(audit, '_inventory', inventory)
    with pytest.raises(ValueError, match='raw evidence changed'):
        audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)


def test_raw_symlink_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'alias.json').symlink_to(tmp_path / 'plan.json')
    with pytest.raises(ValueError, match='symlinks'):
        audit.analyze(tmp_path, expected_source='followup-scripted-QA', require_complete=False)
