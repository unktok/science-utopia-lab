import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_fixed_evaluation_v1 as report
from scripts.reports import native_fixed_evaluation_reproduce_v1 as module
from tests.reports.test_native_fixed_evaluation_report_v1 import fixture, seal
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import file_sha256


def data():
    return report.summarize(*fixture())


def test_all_declared_slots_scores_selections_and_shared_jobs_recompute():
    r = data(); assert module.validate(r) is r
    assert any(p['shared_same_physical_job'] for p in r['paired_reference_differences'])


@pytest.mark.parametrize('change', ['slot', 'null', 'selection', 'tie', 'score', 'measurement',
                                    'duplicate', 'availability', 'policy', 'summary', 'pair'])
def test_rehashed_numeric_or_availability_tampering_is_not_reconstruction(change):
    r = data()
    if change == 'slot': r['search_slots'].reverse()
    elif change == 'null': r['search_slots'][-1]['loss'] = 0
    elif change == 'selection': r['fixed_selection']['throughput:parameters']['selected_id'] = 'fallback'
    elif change == 'tie': r['fixed_selection']['throughput:parameters']['all_tied_ids'] = []
    elif change == 'score': r['physical_worlds'][0]['scores']['throughput'] += 1
    elif change == 'measurement': r['physical_worlds'][0]['measurement']['metrics']['native.accepted_decisions']['value'] += 1
    elif change == 'duplicate': r['physical_worlds'].append(r['physical_worlds'][0])
    elif change == 'availability': r['evaluation_rows'][-1]['physical_job'] = 'invented'
    elif change == 'policy':
        w = next(w for w in r['physical_worlds'] if any(l.startswith('selected:') for l in w['labels']))
        w['policy_sha256'] = '0' * 64
    elif change == 'summary': r['evaluation_summary']['reference:open-seed']['efficiency']['mean'] += 1
    else: r['paired_reference_differences'][0]['differences']['throughput'] += 1
    seal(r)
    with pytest.raises(ValueError): module.validate(r)


def test_all_six_outputs_rebuild_without_raw_audits_or_world_execution(tmp_path):
    p, a, o, b = fixture()
    for name, value in [('plan', p), ('audit-one', a), ('audit-two', a), ('original-plan', o), ('origin-audit', b)]:
        save(tmp_path / (name + '.json'), {k: v for k, v in value.items() if k != 'content_sha256'})
    args = SimpleNamespace(**{n.replace('-', '_'): tmp_path / (n + '.json') for n in
                           ('plan', 'audit-one', 'audit-two', 'original-plan', 'origin-audit')}, output=tmp_path / 'original')
    report.export(args)
    manifest = tmp_path / 'portable.json'
    r = json.loads((args.output / 'report.json').read_text())
    save(manifest, {'schema': report.SCHEMA + '.portable.v1', 'report_content_sha256': r['content_sha256'],
                    'files': {n: file_sha256(args.output / n) for n in module.FILES}})
    result = module.reproduce(args.output / 'report.json', manifest, args.output, tmp_path / 'rebuild')
    assert result['all_six_outputs_byte_identical'] and not result['raw_audit_repeated']
    assert not result['new_native_worlds'] and not result['executable_policy_reconstructed_from_hash']
    with pytest.raises(ValueError, match='fresh independent'):
        module.reproduce(args.output / 'report.json', manifest, args.output, tmp_path / 'rebuild')


def test_retained_actual_closed_matrix_has_no_fallback_or_imputed_graph_results():
    root = Path(__file__).resolve().parents[2]
    r = module.validate(json.loads((root / 'research/data/native-fixed-evaluation-v1/report.json').read_text()))
    assert r['physical_evaluation_worlds'] == 30 and r['logical_evaluation_rows'] == 36
    assert r['unavailable_label_seed_rows'] == 6
    assert sum(s['status'] == 'complete' for s in r['search_slots']) == 5
    assert sum(s['status'] == 'failed' for s in r['search_slots']) == 6
    assert sum(s['status'] == 'not-submitted' for s in r['search_slots']) == 1
    pairs = [p for p in r['paired_reference_differences'] if p['label'] == 'selected:efficiency:parameters'
             and p['reference'] == 'routed-one-accept-all']
    assert len(pairs) == 3 and all(p['differences']['efficiency'] > 0 for p in pairs)
