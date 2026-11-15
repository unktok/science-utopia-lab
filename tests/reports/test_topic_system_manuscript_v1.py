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
        'no own proposal has yet been submitted',
        'reports no completed free-study comparison or gain',
        'not main-track readiness','original native research, production, funding and resource effects remain'):
        assert phrase in text
    entry=(ROOT/'paper/README.md').read_text()
    assert 'current unbuilt source' in entry and '91-page reviewed PDF' in entry
    assert 'unchanged and predates this section' in entry
