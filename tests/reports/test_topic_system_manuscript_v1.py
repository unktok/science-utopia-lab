"""Current source/data boundaries; actual build proof has a separate receipt."""
import json
from pathlib import Path
import re

from tests.reports.test_current_manuscript_estimands import bodies
from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]
SECTION='paper/integrated/native-topic-system-search.tex'


def test_all_current_tracks_inputs_and_crossreferences_survive_source_update():
    current=bodies(); body='\n'.join(current.values())
    assert SECTION in current
    for label in ('sec:problem','sec:design','sec:search','sec:parameter','sec:structural',
        'sec:nested','sec:gradient-evidence','sec:matched','sec:observatory',
        'sec:native-longitudinal-comparison','sec:native-choice-resource',
        'sec:native-topic-system-search','app:reproduction'):
        assert '\\label{'+label+'}' in body
    labels=re.findall(r'\\label\{([^}]+)\}',body)
    assert len(labels)==len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',body))<=set(labels)
    section=current[SECTION]
    assert section.count('{')==section.count('}')
    environments=[]
    for operation,name in re.findall(r'\\(begin|end)\{([^}]+)\}',section):
        if operation=='begin': environments.append(name)
        else: assert environments and environments.pop()==name
    assert not environments


def test_new_hand_control_table_matches_retained_real_results_not_free_invention():
    r=checked(json.loads((ROOT/'research/results/native-legacy-topic-pilot-closed-v1.json').read_text()))
    text=(ROOT/SECTION).read_text()
    assert [w['scores']['throughput'] for w in r['rows']]==[-20.,-36.]
    assert [w['scores']['content-utility'] for w in r['rows']]==[-15.333333333333332,-28.666666666666668]
    assert [w['collected_activity_cost'] for w in r['rows']]==[200.,200.]
    assert 'Core only & $-20$ & $-15.33$ & 200 & 10 & 0' in text
    assert 'Core plus directly related & $-36$ & $-28.67$ & 200 & 18 & 18' in text
    assert 'sixteen\none-year and two two-year projects' in text
    assert '40/3' in text and 'No designer generates a policy.' in text
    assert 'not an automatically invented institution' in text
    assert 'first full scientist request already differs at index 0' in text


def test_declared_objective_and_closed_execution_are_not_retroactive_or_ready_claims():
    text=(ROOT/SECTION).read_text()
    for phrase in ('L_C=-U+0.1K=L_U+0.1K','fixed before these free proposals',
        'never substituted into historical','Missing cost or outcome remains unknown',
        'Unchanged-parent submissions','two each for original throughput',
        'five own native worlds complete',
        'not main-track readiness','original native research, production, funding and resource effects remain'):
        assert phrase in text
    entry=(ROOT/'paper/README.md').read_text()
    assert '98-page integrated draft' in entry and 'Every selected system ties' in entry
    assert 'not a focused main-track-ready' in entry


def test_complete_own_table_and_failure_diagnosis_preserve_retained_original_prefix():
    r=json.loads((ROOT/'research/results/native-topic-free-first-resource-outcomes-v1.json').read_text())
    text=(ROOT/SECTION).read_text()
    assert r['consumed_own_slots_at_stage_entry']==4
    assert r['complete_own_native_outcomes']==3 and r['failed_own_native_outcomes']==1
    assert not r['whole_study_paired_cold_closure']
    assert [s['status'] for s in r['slots']]==['failed','complete']
    assert r['slots'][0]['native_assignment_field_recheck']['core_plus_one_hop_eligible']==[False,True,False,False,False]
    assert all(r['slots'][0]['native_assignment_field_recheck']['canonical_content_equal'])
    assert r['slots'][0]['final_four_fixture_probe_projection']['native_field_errors_per_fixture']==[4,0,4,0]
    assert r['slots'][1]['source_AST_equal_to_strong_parent']
    assert r['slots'][1]['loss']==-8.666666666666668
    for row in ('Throughput & 0 & $-36$ & $-28.67$ & $-8.67$',
        'Content utility & 0 & $-20$ & $-15.33$ & $4.67$',
        'Resource-aware content & 0 & --- & --- & --- & Runtime null',
        'Resource-aware content & 1 & $-36$ & $-28.67$ & $-8.67$',
        'Content utility & 1 & $-36$ & $-28.67$ & $-8.67$',
        'Throughput & 1 & $-36$ & $-28.67$ & $-8.67$'):
        assert row in text
    for phrase in ('not a refill','returned is not accepted','missing cost is not zero',
        'not installed into this closed study','None of the six slots demonstrates'):
        assert phrase in ' '.join(text.split())


def test_complete_study_frozen_selection_role_costs_and_real_figures_match_retention():
    r=json.loads((ROOT/'research/results/native-topic-free-optimization-closed-v1.json').read_text())
    text=' '.join((ROOT/SECTION).read_text().split())
    assert r['consumed_own_slots']==6 and r['complete_own_worlds']==5 and r['runtime_nulls']==1
    assert not r['baseline_fallback']and not r['held_out_evaluation']
    for phrase in ('T0 (also tied with T1), U1 and C1','81 actual charged proposal POSTs, 199 readiness POSTs',
        '19 applied file writes and 56 component probes','3h19m28.15s','2,124 raw files',
        'No new unused condition has been evaluated','conditional incompatibility, not a failed observed world',
        'reference-inclusive incumbent is flat'):
        assert phrase in text
    for path in ('objective-loss-paths-print.png','edit-input-objective-map-print.png'):
        assert 'figures/native-topic-free-v1/'+path in text
        assert (ROOT/'paper/figures/native-topic-free-v1'/path).is_file()
    assert '1,149 & 1,663,354 & 106,971' in text
    assert '199 & 4,056,056 & 9,541' in text
    assert '81 & 2,857,825 & 20,966' in text


def test_conditional_diagnostics_and_prepared_control_are_not_new_scientific_runs():
    r=json.loads((ROOT/'research/results/native-topic-fixed-record-support-v1.json').read_text())
    text=(ROOT/SECTION).read_text()
    assert [(v['positive'],v['zero'],v['negative'])for v in r['rows']]==[(15,5,0),(30,6,0)]
    assert not r['world_level_utility_optimality_proved']
    for phrase in ('B_{\\mathrm{calendar}}','(2,2,2,2,2)','(1,1,2,1,1)',
        'not a global bound','not 32 or 64 native worlds','46/3','86/3',
        'conditional forecast','K=160'):
        assert phrase in text
    prep=json.loads((ROOT/'research/results/native-terminal-cost-opportunity-preparation-v1.json').read_text())
    assert prep['new_native_worlds']==0 and not prep['conditional_forecast']['observed_native_world_improvement']
    assert 'collection avoidance' in text and 'not automatic local 35B invention' in text
