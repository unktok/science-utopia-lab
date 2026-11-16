"""Pure SCRIPTED matched arithmetic and retained software-only export checks."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_consumer_source_comparison_v1 as reader
from tests.reports.test_native_topic_free_readout_v1 import fixture as old_fixture
from utopia.optimization.native_consumer_evidence_v1 import OPTION
from utopia.system.design_patch import clone, digest


def fixture(*, null=None):
    p, a, old, observations = old_fixture()
    p.update(schema=reader.STUDY + '.plan', arms=reader.ARMS, objectives=reader.OBJECTIVES)
    p['reference_order'] = reader.REFERENCES
    p['reference_systems']['terminal-consolidation'] = clone(p['reference_systems']['core-plus-related'])
    p['schedule'] = [{'arm': arm, 'objective': obj, 'generation': g}
                     for g in range(2) for arm in reader.ARMS for obj in reader.OBJECTIVES]
    evidence = {'SCRIPTED': 'not actual source cards'}
    p['strategies_by_arm'] = {arm: {'local-workflow-designer':
        ({OPTION: evidence} if arm == 'literal-consumers' else {})} for arm in reader.ARMS}
    p['content_sha256'] = digest({k: v for k, v in p.items() if k != 'content_sha256'})
    worlds = [clone(w) for w in a['worlds'] if w['role'] == 'developer-reference']
    obs = {w['identity']: clone(observations[w['identity']]) for w in worlds}
    third = clone(worlds[1]); third['identity'] = 'workflow-reference-terminal-consolidation'
    o = clone(obs[worlds[1]['identity']]); o['suggestion_id'] = third['identity']
    worlds.append(third); obs[third['identity']] = o
    records = {}; selected = {}
    for slot in p['schedule']:
        arm, obj, g = slot['arm'], slot['objective'], slot['generation']
        record = clone(old[obj, g]); request = record['request']
        request['strategy_provenance'] = clone(p['strategies_by_arm'][arm]['local-workflow-designer'])
        request['developer_reference_context'] = {'summary': [
            {'reference': 'workflow-reference-' + label} for label in reader.REFERENCES[:2]]}
        record['request_sha256'] = digest(request)
        identity = arm + '-' + obj + '-' + str(g)
        if null == (arm, obj, g):
            record.update(observations=[], draws=[], generation_error={'SCRIPTED': 'consumed missing submission'})
        else:
            o = record['observations'][0]; old_id = o['suggestion_id']; o['suggestion_id'] = identity
            w = clone(next(w for w in a['worlds'] if w['identity'] == old_id))
            w.update(identity=identity, arm=arm); worlds.append(w); obs[identity] = o
        records[arm, obj, g] = record
    for arm in reader.ARMS:
        for obj in reader.OBJECTIVES:
            pool = [o for (ar, ob, g), r in records.items() if ar == arm and ob == obj for o in r['observations']]
            best = min((o['loss'] for o in pool), default=None)
            ties = [o for o in pool if o['loss'] == best]
            selected[arm + '::' + obj] = {'loss': best, 'all_tied_ids': [o['suggestion_id'] for o in ties],
                'selected_id': ties[0]['suggestion_id'] if ties else None, 'system': ties[0]['candidate'] if ties else None}
    a.update(schema=reader.STUDY + '.audit', plan_sha256=p['content_sha256'], worlds=worlds,
             selection={'selected': selected, 'baseline_fallback': False})
    a['content_sha256'] = digest({k: v for k, v in a.items() if k != 'content_sha256'})
    return p, a, records, obs


def test_all_arms_objectives_slots_paths_and_withheld_comparator_are_distinct():
    result = reader.analyze(*fixture())
    assert result['consumed_own_slots'] == 8 and result['physical_worlds'] == 11
    assert len(result['loss_paths']) == 4
    assert [r['optimizer_visible'] for r in result['references']] == [True, True, False]
    assert result['literal_consumers_minus_interface_own_best'] == dict.fromkeys(reader.OBJECTIVES, 0.0)
    assert sum(r['source_evidence_visible'] for r in result['slots']) == 4
    assert not result['interpretation']['independent_optimizer_replications']
    assert not result['interpretation']['equal_measured_compute_claimed']


def test_missing_slot_is_not_filled_filtered_or_a_zero_cost():
    result = reader.analyze(*fixture(null=('interface-only', 'content-utility', 0)))
    row = result['slots'][0]
    assert len(result['slots']) == 8 and result['physical_worlds'] == 10
    assert row['status'] == 'generation-null' and row['loss'] is None
    assert row['metrics'][reader.METRIC]['value'] is None and row['requested_activity_cost'] is None
    assert result['loss_paths']['interface-only::content-utility'][0]['best_own_loss'] is None


def test_finisher_uses_actual_original_cost_stage_filenames(tmp_path, monkeypatch):
    from scripts import finish_native_consumer_source_readouts_v1 as continuation
    captured = {}
    monkeypatch.setattr(continuation, 'finish', lambda args, **kw: captured.update(kw))
    monkeypatch.setattr(continuation, 'ROOT', tmp_path / 'reader-source')
    continuation.run(SimpleNamespace(frozen_source=tmp_path / 'source', analysis=tmp_path / 'analysis',
                                     output=tmp_path / 'external-output'))
    extra = captured['report_extra_arguments']
    assert extra[3] == str(tmp_path / 'analysis/costs-1.json')
    assert extra[5] == str(tmp_path / 'analysis/costs-2.json')
    assert captured['preceding_schema'] == reader.STUDY + '.finish'


@pytest.mark.parametrize('location', ['reader', 'scientific', 'symlink'])
def test_finisher_rejects_source_local_output_before_wait_or_directory_creation(tmp_path, monkeypatch, location):
    from scripts import finish_native_consumer_source_readouts_v1 as continuation
    reader_source, scientific_source = tmp_path / 'reader', tmp_path / 'scientific'
    reader_source.mkdir(); scientific_source.mkdir()
    monkeypatch.setattr(continuation, 'ROOT', reader_source)
    monkeypatch.setattr(continuation, 'finish', lambda *a, **k: pytest.fail('must reject before wait or writes'))
    if location == 'symlink':
        link = tmp_path / 'external-looking-link'
        link.symlink_to(scientific_source, target_is_directory=True)
        output = link / 'new-report'
    else:
        output = (reader_source if location == 'reader' else scientific_source) / 'new-report'
    with pytest.raises(ValueError, match='outside both reader and scientific sources before waiting'):
        continuation.run(SimpleNamespace(frozen_source=scientific_source, output=output))
    assert not output.exists()


@pytest.mark.parametrize('mutation', ['visibility', 'reference', 'selection', 'loss', 'slot'])
def test_wrong_visibility_withheld_leak_reselection_and_missing_records_are_rejected(mutation):
    p, a, r, o = fixture()
    if mutation == 'visibility':
        r[next(iter(r))]['request']['strategy_provenance'][OPTION] = {'SCRIPTED': 'leak'}
        r[next(iter(r))]['request_sha256'] = digest(r[next(iter(r))]['request'])
    elif mutation == 'reference':
        r[next(iter(r))]['request']['developer_reference_context']['summary'].append(
            {'reference': 'workflow-reference-terminal-consolidation'})
        r[next(iter(r))]['request_sha256'] = digest(r[next(iter(r))]['request'])
    elif mutation == 'selection':
        a['selection']['selected']['interface-only::content-utility']['selected_id'] = 'workflow-reference-core-only'
    elif mutation == 'loss':
        o[next(iter(o))]['loss'] = -999
    else:
        r.pop(next(iter(r)))
    with pytest.raises(ValueError):
        reader.analyze(p, a, r, o)


@pytest.mark.skipif(not os.environ.get('SCIENCE_UTOPIA_CONSUMER_SAVED_QA'), reason='saved SCRIPTED public closure required')
def test_two_readonly_exports_from_original_saved_scripted_closure(tmp_path, monkeypatch):
    """No inference/Docker/world/source execution; original public QA must already exit."""
    fixture_root = Path(os.environ['SCIENCE_UTOPIA_CONSUMER_SAVED_QA']).resolve()
    run = fixture_root / 'free-study'
    plan = json.loads((run / 'plan.json').read_text())
    frozen = Path(os.environ['SCIENCE_UTOPIA_CONSUMER_SAVED_SOURCE']).resolve()
    # Public QA retained original worker outputs without copying/resealing.
    audit = fixture_root / 'audit-retained.json'; cost = fixture_root / 'cost-retained.json'
    assert audit.is_file() and cost.is_file() and (fixture_root / 'verification.json').is_file()
    audit_two, cost_two = tmp_path / 'audit-two.json', tmp_path / 'cost-two.json'
    audit_two.write_bytes(audit.read_bytes()); cost_two.write_bytes(cost.read_bytes())
    from openai import OpenAI
    monkeypatch.setattr(OpenAI, '__init__', lambda *a, **k: pytest.fail('read-only reader cannot construct model SDK'))
    with tempfile.TemporaryDirectory(prefix='consumer-saved-software-readout-') as external:
        outputs = [Path(external) / ('export-' + str(i)) for i in (1, 2)]
        for output in outputs:
            reader.export(SimpleNamespace(run=run, frozen_source=frozen, audit_one=audit, audit_two=audit_two,
                cost_one=cost, cost_two=cost_two, output=output))
        for name in ('report.json', 'slots.csv', 'manifest.json'):
            assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
        report = json.loads((outputs[0] / 'report.json').read_text())
    assert report['scientific_source_commit'] == plan['source_commit']
    assert len(report['slots']) == 8 and report['physical_worlds'] == 11
    assert len(report['behavior_evidence']['construction']) == 8
    assert len(report['behavior_evidence']['world_request_sequences']) == 11
    assert not report['interpretation']['publication_ready']
