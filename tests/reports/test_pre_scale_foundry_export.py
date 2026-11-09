"""SYNTHETIC offline Foundry projection QA; no inference/native execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import export_pre_scale_design_evidence as exporter
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_pre_scale_search_report import fixture, rehash
from tests.reports.test_pre_scale_search_v1 import plan
from utopia.runtime.checkpointing import write_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def reseal(root, audit):
    inventory = _inventory(root)
    audit.update(raw_inventory_sha256=digest(inventory), raw_files=len(inventory))
    return rehash(audit)


def inputs(root, monkeypatch):
    audit = fixture(root); p = plan()
    monkeypatch.setattr(exporter, 'SOURCE', p['source_commit'])
    monkeypatch.setattr(exporter, 'PLAN', p['content_sha256'])
    audit.update(source_proof={'status': 'verified-exact-source-closure'}, new_model_calls=0,
        new_code_executions=0)
    closure = {'plan_sha256': p['content_sha256'],
        'selection_sha256': audit['selection']['content_sha256']}
    write_json_atomic(root/'complete.json', {**closure, 'content_sha256': digest(closure)}, sort_keys=True)
    world = audit['worlds'][0]; assert world['identity'] == 'reference-open-seed'
    spec = SystemSpec.from_dict(world['system'])
    directory = root/'references/open-seed/worlds/reference-open-seed-s41001/simulation/checkpoints/native-design'
    directory.mkdir(parents=True)
    annual = []
    for year in range(1, 5):
        path = directory/f'portable_checkpoint_year_{year}.json.gz'
        state = {'year': year, 'native_system': {'spec': spec.to_dict(),
            'system_fingerprint': spec.fingerprint, 'events': [{'year': i, 'phase': 0,
                'event_type': 'SYNTHETIC-QA', 'provenance': {}, 'payload': {}} for i in range(1, year+1)]},
            'ecosystem_data': {'agents': [{'id': 'SYNTHETIC-ACTOR', 'type': 'author',
                'resources': 10., 'is_active': True, 'can_author': True}]},
            'paper_tracker': {'papers': []}}
        write_portable_checkpoint(path, state)
        annual.append({'year': year, 'checkpoint_sha256': file_sha256(path),
            'interval_llm_elapsed_seconds': 0.})  # Explicit synthetic fixture timing.
    world['physical_proof']['annual_checkpoints'] = annual
    return p, reseal(root, audit)


def test_all_eight_arm_exports_keep_unsubmitted_slots_without_inventing_candidate_worlds(tmp_path, monkeypatch):
    root = tmp_path/'SYNTHETIC'; p, audit = inputs(root, monkeypatch)
    before = _inventory(root); original = deepcopy(audit)
    result = exporter.build(root, p, audit)
    assert _inventory(root) == before and audit == original and len(result) == 8
    for name, envelope in result.items():
        payload = json.loads(envelope['payload_json'])
        assert name == payload['interpretation']['pre_scale_arm'].replace(':', '--')+'.json'
        assert len(payload['systems']) == 1
        assert len(payload['interpretation']['unsubmitted_slots']) == 2
        assert payload['pending'] is None and payload['relaxation'] is None
        assert payload['interpretation']['development_only']
        assert payload['interpretation']['live_player_intervention'] is False
        row = payload['systems'][0]
        assert row['evidence_label'].startswith('INITIAL REFERENCE')
        assert row['native_loss'] == 0 and len(row['runs'][0]['frames']) == 4
        assert row['runs'][0]['frames'][0]['actors'][0]['id'] == 'SYNTHETIC-ACTOR'
        assert row['difference']['nodes_added'] == row['difference']['nodes_changed'] == []
        assert envelope == exporter.envelope(payload)


@pytest.mark.parametrize('part', ['source', 'plan', 'closure', 'inventory', 'audit-scope'])
def test_export_requires_original_closed_source_and_inventory(tmp_path, monkeypatch, part):
    root = tmp_path/'SYNTHETIC'; p, audit = inputs(root, monkeypatch)
    if part == 'source':
        p['source_commit'] = '0'*40; rehash(p)
    elif part == 'plan':
        p['budget']['total_native_worlds_upper_bound'] = 100; rehash(p)
    elif part == 'closure':
        (root/'complete.json').unlink()
    elif part == 'inventory':
        write_json_atomic(root/'SYNTHETIC-extra-file.json', {'unexpected': True})
    else:
        audit['source_proof']['status'] = 'not-a-full-original-audit'; rehash(audit)
    with pytest.raises((ValueError, FileNotFoundError)):
        exporter.build(root, p, audit)


def test_partial_failure_has_no_fabricated_year_or_actor_frame(tmp_path):
    spec = plan()['reference_systems']['open-seed']
    world = {'system': spec, 'physical_proof': {'status': 'partial-or-technical-failure',
        'annual_checkpoints': []}}
    assert exporter.cell_run(tmp_path/'not-created', world, years=4) == []
    assert not (tmp_path/'not-created').exists()


def test_submitted_failed_candidate_keeps_its_source_and_exact_error_without_fabricated_activity(tmp_path, monkeypatch):
    root = tmp_path/'SYNTHETIC'; p, audit = inputs(root, monkeypatch)
    arm = 'throughput:parameters'; identity = 'SYNTHETIC-failed-candidate'
    row = next(r for r in audit['selection']['all_rows'] if r['row_id'] == f'run-00:{arm}:g0')
    system = deepcopy(audit['selection']['reference_systems']['open-seed'])
    row.update(system=system, status='failed', forward_complete=False)
    error = {'error_type': 'SYNTHETIC-QA', 'error': 'SYNTHETIC failure, not native scientific evidence'}
    audit['worlds'].insert(6, {'identity': identity, 'role': 'search:'+arm, 'seed': 41001,
        'system': system, 'status': 'failed', 'scores': deepcopy(row['cross_scores']),
        'physical_proof': {'status': 'partial-or-technical-failure', 'annual_checkpoints': [], 'measurement': None}})
    path = root/'search/run-00/throughput--parameters/campaign/native-adaptive-state.json'
    state = json.loads(path.read_text()); record = state['records'][0]
    record.update(generation_error=None, observations=[{'suggestion_id': identity,
        'candidate': system, 'status': 'failed', 'loss': None, 'metadata': {'technical_failures': [error]}}])
    write_json_atomic(path, state, sort_keys=True); reseal(root, audit)
    payload = json.loads(exporter.build(root, p, audit)['throughput--parameters.json']['payload_json'])
    candidate = payload['systems'][1]
    assert candidate['runs'] == [] and candidate['native_loss'] is None
    assert candidate['status'] == 'failed' and candidate['technical_failures'] == [error]
    assert json.loads(candidate['system_spec_json']) == SystemSpec.from_dict(system).to_dict()
    assert len(payload['interpretation']['unsubmitted_slots']) == 1


def test_optional_actual_completed_cell_can_supply_original_years_actors_and_events_without_simulation():
    root = Path('/Users/shiro/unktok/dev/science-utopia-lab-experiments/pre-scale-search-v1-a1/outputs/pre-scale-search-v1-a1/search/run-00/efficiency--parameters/worlds/native-adaptive-0d2c363a8de1c78e14d10962-s41001')
    if not (root/'system.json').is_file():
        pytest.skip('optional immutable actual completed numeric cell unavailable')
    spec = json.loads((root/'system.json').read_text()); before = _inventory(root)
    directory = root/'simulation/checkpoints/native-design'
    annual = [{'year': year, 'checkpoint_sha256': file_sha256(directory/f'portable_checkpoint_year_{year}.json.gz')}
        for year in range(1, 5)]
    result = exporter.cell_run(root, {'system': spec, 'seed': 41001,
        'physical_proof': {'status': 'complete', 'annual_checkpoints': annual}}, years=4)
    assert _inventory(root) == before
    assert [frame['year'] for frame in result[0]['frames']] == [1, 2, 3, 4]
    assert all(len(frame['actors']) == 5 for frame in result[0]['frames'])
    assert result[0]['events'] and result[0]['seed'] == 41001


@pytest.mark.parametrize('part', ['checkpoint-hash', 'year', 'spec', 'prefix', 'incomplete'])
def test_frame_content_and_committed_horizon_are_not_guessed(tmp_path, monkeypatch, part):
    root = tmp_path/'SYNTHETIC'; p, audit = inputs(root, monkeypatch)
    world = audit['worlds'][0]; annual = world['physical_proof']['annual_checkpoints']
    directory = root/'references/open-seed/worlds/reference-open-seed-s41001/simulation/checkpoints/native-design'
    if part == 'incomplete':
        annual.pop()
    else:
        from utopia.runtime.checkpointing import read_portable_checkpoint
        path = directory/'portable_checkpoint_year_2.json.gz'
        state = read_portable_checkpoint(path)
        if part == 'year': state['year'] = 3
        elif part == 'spec': state['native_system']['spec']['metadata']['SYNTHETIC-wrong-spec'] = True
        elif part == 'prefix': state['native_system']['events'][0]['event_type'] = 'SYNTHETIC-changed-history'
        else: state['paper_tracker']['papers'] = ['SYNTHETIC-change']
        write_portable_checkpoint(path, state)
        if part != 'checkpoint-hash': annual[1]['checkpoint_sha256'] = file_sha256(path)
    reseal(root, audit)
    with pytest.raises(ValueError): exporter.build(root, p, audit)


def test_concurrent_raw_change_stops_export_without_creating_an_output(tmp_path, monkeypatch):
    root = tmp_path/'SYNTHETIC'; p, audit = inputs(root, monkeypatch)
    real = exporter.cell_run; changed = False
    def mutate(*args, **kwargs):
        nonlocal changed
        if not changed:
            write_json_atomic(root/'SYNTHETIC-concurrent.json', {'writer': 'SYNTHETIC'}); changed = True
        return real(*args, **kwargs)
    monkeypatch.setattr(exporter, 'cell_run', mutate)
    with pytest.raises(ValueError, match='changed during'):
        exporter.build(root, p, audit)
