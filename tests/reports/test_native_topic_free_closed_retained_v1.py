"""Retained-file/data checks only, not a new original audit or native run."""
import csv
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.system import SystemSpec

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/native-topic-free-optimization-v1'


def read(path):return json.loads(path.read_text())


def test_all_eight_original_programs_and_exact_selection_bytes_survive():
    m=read(DATA/'systems-manifest.json')
    assert len(m['files_sha256'])==9 and m['includes_failed_submission']
    for name,sha in m['files_sha256'].items():
        assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==sha
    selected=checked(read(DATA/'selection.json'))
    assert not selected['baseline_fallback']and not selected['held_out_evaluation']
    for objective,label in m['selection_labels'].items():
        candidate=read(DATA/'systems'/f'{label}.json')
        assert selected['selected'][objective]['system']==candidate
        assert SystemSpec.from_dict(candidate).fingerprint
    assert (DATA/'systems/content-utility-g1.json').read_bytes()==(DATA/'systems/core-plus-related.json').read_bytes()


def test_original_slot_csv_matches_all_compact_losses_and_retained_runtime_null():
    r=read(ROOT/'research/results/native-topic-free-optimization-closed-v1.json')
    with (DATA/'slots.csv').open()as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==6 and r['complete_own_worlds']==5 and r['runtime_nulls']==1
    for original,retained in zip(rows,r['rows']):
        assert original['objective']==retained['objective']and int(original['generation'])==retained['generation']
        assert original['status']==retained['status']
        for label,column in (('T','throughput'),('U','content-utility'),('C','resource-aware-content'),('K','collected_resource_cost')):
            assert (None if original[column]==''else float(original[column]))==retained[label]
    assert all(r['rows'][2][key]is None for key in ('T','U','C','K'))
    assert not r['held_out_evaluation']and not r['independent_optimizer_replications']and not r['publication_ready']


def test_retained_used_figures_and_effect_projection_equal_source_bound_exports():
    receipt=read(ROOT/'research/results/native-topic-effect-map-retention-v1.json')
    for name,sha in receipt['files_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    effect=checked(read(ROOT/'research/data/native-topic-effect-map-v1/report.json'))
    closed=read(ROOT/'research/results/native-topic-free-optimization-closed-v1.json')
    assert effect['readout_content_sha256']==closed['paired_readout']['report_content_sha256']
    assert len(effect['rows'])==6
    assert [r['delta_from_best_visible_reference']for r in effect['rows']]==[0.,13.333333333333336,None,0.,0.,0.]
    assert all(not r['submitted_change'][key]for r in effect['rows']for key in
        ('added_nodes','removed_nodes','added_connections','removed_connections','phase_updates','added_schedules','removed_schedules'))


def test_cost_and_construction_counts_are_distinct_and_load_unknown_is_not_zero():
    r=read(ROOT/'research/results/native-topic-free-optimization-closed-v1.json')
    assert r['authoring']['completed_editor_steps']==81
    assert r['authoring']['actual_proposal_POSTs']==81
    assert r['authoring']['actual_readiness_POSTs']==199
    assert r['authoring']['component_probes']==56
    c=r['cost_summary'];assert c['load_token_usage']is None
    assert c['scientist_prompt_tokens']+c['scientist_completion_tokens']==1770325
    assert c['scientist_cached_prompt_subset']<c['scientist_prompt_tokens']
    assert not c['cache_counts_added_to_prompt_counts']and not c['nested_durations_added']
