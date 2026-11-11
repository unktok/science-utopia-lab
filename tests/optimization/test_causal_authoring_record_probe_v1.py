from types import SimpleNamespace

import pytest

from scripts import probe_causal_authoring_records_v1 as probe
from tests.optimization.test_native_causal_design import anchor
from utopia.optimization.native_numeric_designer import save, checked
from utopia.utils.data_utils import file_sha256


def context():
    return {'inputs': {'observations': [{'payload': {'conferences': {'conferences': [
        {'conference_id':'c', 'submitted_papers':[{'id':'p'}]}]}}}]}}


def test_emitted_summary_counts_literal_decisions_not_native_outcomes():
    output = {'outputs': {'decisions': [{'payload': {'conference_id':'c', 'paper_id':'p', 'decision':'accept'}}]}}
    summary = probe.emitted_summary(output, context())
    assert summary['decision_labels'] == {'accept': 1}
    assert summary['exact_identity_coverage'] is True
    assert summary['native_receiver_executed'] is False and summary['new_loss'] is None
    output['outputs']['decisions'] *= 2
    summary = probe.emitted_summary(output, context())
    assert summary['exact_identity_coverage'] is False and summary['duplicate_identity_count'] == 1
    output['outputs']['decisions'][0]['payload']['paper_id'] = ['untrusted', {'json': True}]
    assert probe.emitted_summary(output, context())['exact_identity_coverage'] is False


@pytest.mark.parametrize('baseline_fails', [True, False])
def test_probe_stops_on_baseline_failure_but_charges_all_known_candidate_failures(tmp_path, monkeypatch, baseline_fails):
    output = {'outputs': {'decisions': [{'payload': {'empty_cycle': True}}]}, 'state': {}}
    plan = {'source_commit':'SCRIPTED', 'protocol_sha256':file_sha256(probe.ROOT/probe.PROTOCOL),
        'image_id':'SCRIPTED', 'audit_file_sha256':'SCRIPTED', 'interpretation':'SCRIPTED',
        'frames':[{'artifact':{'original':True}, 'context':{}, 'result':output, 'bundle_sha256':str(i)} for i in range(4)],
        'candidates':[{'id':str(i),'system':anchor().to_dict()} for i in range(8)]}
    # Use the actual candidate image identity but fake all execution transport.
    selection = next(n for n in anchor().mechanisms if n.mechanism_id == 'world.selection')
    plan['image_id'] = selection.parameters['runtime_image_id']
    for frame in plan['frames']:
        frame['context'] = {'period':1}
    save(tmp_path/'plan.json', plan)
    calls = []
    class Executor:
        def __init__(self, image, timeout):
            self.image_id = image
            assert timeout == 15
        def execute(self, artifact, context):
            calls.append(artifact)
            if artifact.get('original'):
                return SimpleNamespace(result={} if baseline_fails else output, receipt={})
            raise ValueError('SCRIPTED failed candidate, not a retry invitation')
    monkeypatch.setattr(probe, 'pinned_revision', lambda root:'SCRIPTED')
    monkeypatch.setattr(probe, 'DockerCodeExecutor', Executor)
    if baseline_fails:
        with pytest.raises(ValueError, match='did not replay'):
            probe.run(tmp_path)
        assert len(calls) == 1
        assert not (tmp_path/'report.json').exists()
    else:
        probe.run(tmp_path)
        report = checked(probe.read(tmp_path/'report.json'))
        assert len(calls) == 36 and len(report['slots']) == 8
        assert all(len(s['frames']) == 4 and s['status'] == 'one-or-more-frames-failed' for s in report['slots'])
        assert report['measured_candidate_losses'] == report['native_worlds'] == report['model_calls'] == 0
    with pytest.raises(FileExistsError):
        probe.run(tmp_path)
