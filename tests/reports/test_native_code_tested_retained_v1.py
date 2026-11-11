"""Retained closed-cohort interpretation and exact data/figure hash bindings."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/native-code-tested-loop-v1'


def read(path):return json.loads(path.read_text())


def test_exact_retained_report_cost_and_figures_match_closed_manifest_and_receipt():
    receipt=read(ROOT/'research/results/native-code-tested-loop-closed-verification-v1.json')
    report=checked(read(DATA/'report.json'));manifest=checked(read(DATA/'manifest.json'));cost=checked(read(DATA/'costs.json'))
    assert report['content_sha256']==receipt['report_content_sha256']
    assert file_sha256(DATA/'report.json')==receipt['report_file_sha256']
    assert file_sha256(DATA/'costs.json')==receipt['cost_file_sha256']
    assert cost['input_audit_content_sha256']==report['audit_sha256']==receipt['audit_content_sha256']
    for name,sha in manifest['files'].items():
        path=DATA/name if (DATA/name).exists() else ROOT/'paper/figures/native-code-tested-loop-v1'/name
        assert file_sha256(path)==sha


def test_all_slots_failures_ties_and_actual_versioned_probe_results_remain_visible():
    report=checked(read(DATA/'report.json'));slots=report['slots']
    assert len(slots)==4 and len(report['physical_worlds'])==7 and len(report['references'])==3
    assert [r['status'] for r in slots]==['failed','complete','complete','failed']
    assert all(r['changed_paths']==['/mechanisms/7/parameters/code_artifact/source'] for r in slots)
    assert not any(r['connections_changed'] or r['schedules_changed'] or r['nodes_added'] or r['nodes_removed'] for r in slots)
    assert sum(r['component_trace']['component_testing']['probe_attempts'] for r in slots)==32
    comparisons=[c for r in slots for c in r['component_trace']['same_fixture_later_code_comparisons']]
    assert not any(c['transition']=='raised-to-returned' for c in comparisons)
    assert sum(c['transition']=='returned-to-raised' for c in comparisons)==4
    assert sum(c['transition']=='returned-to-returned' for c in comparisons)==12
    final=[r['component_trace']['drawn_candidate_artifact_observations']['components'][0]['test_applicability'] for r in slots]
    assert final==['same-current-artifact','current-artifact-untested','current-artifact-untested','current-artifact-untested']
    assert report['frozen_selection']['throughput:code-and-graph']['selected_id'] is None
    efficiency=report['frozen_selection']['efficiency:code-and-graph']
    assert efficiency['completed_submissions']==2 and len(efficiency['all_tied_ids'])==2
    assert efficiency['selected_id']==efficiency['all_tied_ids'][0]
    references={r['label']:r for r in report['references']}
    assert efficiency['loss']==references['reviewed-accept-all']['scores']['efficiency']
    assert efficiency['loss']>references['routed-one-accept-all']['scores']['efficiency']
    assert not report['interpretation']['publication_ready'] and not report['interpretation']['held_out_evaluation']
