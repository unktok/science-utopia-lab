"""Current unbuilt source/data boundaries; not TeX build or visual evidence."""
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
    assert 'first full scientist request already differs at index0' in text


def test_prospective_objective_and_execution_are_not_retroactive_or_completed_results():
    text=(ROOT/SECTION).read_text()
    for phrase in ('L_C=-U+0.1K=L_U+0.1K','fixed before these free proposals',
        'never substituted into historical','Missing cost or outcome remains unknown',
        'Unchanged-parent submissions','two each for original throughput',
        'not a normally closed all-slot audit',
        'three own native worlds complete',
        'not main-track readiness','original native research, production, funding and resource effects remain'):
        assert phrase in text
    entry=(ROOT/'paper/README.md').read_text()
    assert 'current unbuilt source' in entry and '91-page reviewed PDF' in entry
    assert 'unchanged and predates this section' in entry


def test_partial_own_table_and_failure_diagnosis_match_retained_original_prefix():
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
        'Resource-aware content & 1 & $-36$ & $-28.67$ & $-8.67$'):
        assert row in text
    for phrase in ('not a refill','returned is not accepted','missing cost is not zero',
        'not installed into this running study','None of these four slots demonstrates'):
        assert phrase in text


def test_conditional_diagnostics_and_prepared_control_are_not_new_scientific_runs():
    r=json.loads((ROOT/'research/results/native-topic-fixed-record-support-v1.json').read_text())
    text=(ROOT/SECTION).read_text()
    assert [(v['positive'],v['zero'],v['negative'])for v in r['rows']]==[(15,5,0),(30,6,0)]
    assert not r['world_level_utility_optimality_proved']
    for phrase in ('B_{\\mathrm{calendar}}','(2,2,2,2,2)','(1,1,2,1,1)',
        'not a global bound','not32 or64 native worlds','46/3','86/3',
        'conditional forecast','K=160'):
        assert phrase in text
    prep=json.loads((ROOT/'research/results/native-terminal-cost-opportunity-preparation-v1.json').read_text())
    assert prep['new_native_worlds']==0 and not prep['conditional_forecast']['observed_native_world_improvement']
    assert 'collection avoidance' in text and 'not automatic local35B invention' in text
