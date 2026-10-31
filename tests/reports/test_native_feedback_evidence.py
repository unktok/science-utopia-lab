"""Frozen live development evidence must not drift into success claims."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def test_recorded_native_source_and_gradient_negative_results():
    sources = [load(f'research/results/{name}.audit.json') for name in (
        'native-feedback-source-v2', 'native-feedback-source-v2-a2',
        'native-feedback-source-v2-a3')]
    assert [[r['loss'] for r in s['rows']] for s in sources] == [
        [-1., -1., -1.], [-1., -1., -1.], [-2., -2.]]
    assert all(r['delivered_messages'] == 0 for s in sources for r in s['feedback_activity'])
    proposals = [p for s in sources for p in s['proposals']]
    assert len(proposals) == 5
    assert len({p['source_sha256'] for p in proposals}) == 1
    assert sources[-1]['proposals'][0]['technical_repairs'] == 1
    assert sources[-1]['proposals'][0]['plan_sha256']
    gradient = load('research/results/native-feedback-gradient-v2.audit.json')
    assert gradient['full_native_world_autograd'] is False
    assert [r['loss'] for r in gradient['rows']] == [-1., -1.]
    assert gradient['reports'][0]['gradient'] == [0.]
    assert gradient['reports'][0]['mean_before'] == gradient['reports'][0]['mean_after']
    assert all(r['wire'][0]['contexts_by_year'] == {'2': 6} for r in gradient['rows'])


def test_actual_completed_job_figure_and_provenance():
    manifest = load('paper/figures/native-design-job.manifest.json')
    for key in ('image', 'browser_report', 'native_audit'):
        assert hashlib.sha256((ROOT / manifest[key]).read_bytes()).hexdigest() == manifest[key + '_sha256']
    browser = load(manifest['browser_report'])
    audit = load(manifest['native_audit'])
    assert browser['jobId'] == audit['job']['job_id'] == manifest['job_id']
    assert audit['job']['source_commit'] == manifest['worker_source_commit']
    assert manifest['renderer_source_commit'][:12] in browser['rendererService']
    assert manifest['worker_source_commit'][:12] in browser['runProvenance']
    assert browser['errors'] == [] and browser['mobileOverflow'] is False
    assert audit['job']['result']['native_loss'] == -3.
    assert audit['job']['same_society_migration'] is False
