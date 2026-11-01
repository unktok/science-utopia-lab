"""Staged exact journal/receipt reconstruction using scripted non-native data."""
import pytest

from scripts.analyze_native_joint_objectives_v5 import audit_proposals
from tests.optimization.test_native_joint_analysis_v5 import authored_fixture


@pytest.mark.parametrize('thinking', [False, True])
def test_staged_plan_repair_source_success_reconstruct_exactly(authored_fixture, thinking):
    f = authored_fixture(staged=True, thinking=thinking)
    report = audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)
    assert report[0]['plan_draft_count'] == 2
    assert report[0]['source_draft_count'] == 1
    assert report[0]['status'] == 'isolated-native-region-passed-not-native-evaluated'
    assert report[0]['structure_only_placeholder_executions'] == 0
    assert len(f.executed_sources) == 1  # Original scripted source probe only.
    assert 'STRUCTURE_ONLY_NOT_A_CANDIDATE' not in f.executed_sources[0]
    assert [r['phase'] for r in report[0]['receipts']] == ['plan', 'plan', 'source']


@pytest.mark.parametrize('phase', ['plan', 'source', 'runtime'])
def test_staged_phase_exhaustion_is_null_unexecuted_native_candidate(authored_fixture, phase):
    f = authored_fixture(staged=True, success=False, failure_phase=phase)
    report = audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)
    assert report[0]['status'] == 'invalid-technical-manifest'
    assert report[0]['candidate_fingerprint'] is None
    assert report[0]['terminal_phase'] == ('plan' if phase == 'plan' else 'source')
    assert report[0]['plan_draft_count'] == (3 if phase == 'plan' else 1)
    assert report[0]['source_draft_count'] == (0 if phase == 'plan' else 3)
    assert report[0]['failed_probe_error_preserved_not_reexecuted'] is (phase == 'runtime')
    assert report[0]['structure_only_placeholder_executions'] == 0
    assert len(f.controller.state['records']) == 1


def test_staged_plan_to_source_link_tamper_fails(authored_fixture):
    import json
    f = authored_fixture(staged=True)
    path = f.run / 'arms' / f.arm / 'design-proposals/region-1-0.json'
    saved = json.loads(path.read_text())
    saved['binding']['plan_sha256'] = 'not-the-selected-plan'
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='receipt hash chain differs'):
        audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)
