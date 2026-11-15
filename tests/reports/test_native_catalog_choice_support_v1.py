"""Retained support arithmetic/source identities, not native policy feasibility."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def report():
    return checked(json.loads((ROOT/'research/results/native-catalog-choice-support-screen-v1.json').read_text()))


def test_actual_founder_choice_sets_and_duration_arithmetic_remain_distinct():
    r=report();rows=r['actors'];cap=r['papers_per_project'];years=r['years']
    assert len(rows)==5 and len({row['actor_id'] for row in rows})==5
    for row in rows:
        core=row['core_topic_years'];legacy=row['legacy_core_plus_related_topic_years']
        assert set(core)<=set(legacy) and all(legacy[t]==d for t,d in core.items())
        assert all(type(d) is int and d>0 for d in legacy.values())
        assert row['core_minimum_years']==min(core.values())
        assert row['legacy_core_plus_related_minimum_years']==min(legacy.values())
        assert row['shortest_legacy_topics']==sorted(t for t,d in legacy.items() if d==min(legacy.values()))
        assert row['conditional_four_year_core_outputs']==cap*(years//min(core.values()))
        assert row['conditional_four_year_legacy_outputs']==cap*(years//min(legacy.values()))
    assert sum(row['conditional_four_year_core_outputs'] for row in rows)==r['conditional_core_duration_arithmetic']==20
    assert sum(row['conditional_four_year_legacy_outputs'] for row in rows)==r['conditional_legacy_duration_arithmetic']==36


def test_retained_source_hashes_reconstruct_from_original_commit_not_live_raw():
    r=report();seen=set()
    for path,expected in r['inputs'].items():
        if '/utopia/' not in path or not path.endswith('.py'):continue
        relative='utopia/'+path.split('/utopia/',1)[1]
        original=subprocess.check_output(['git','show',r['scientific_source_commit']+':'+relative],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==expected
        seen.add(relative)
    assert len(seen)==6


def test_arithmetic_never_claims_native_gain_feasibility_or_a_global_bound():
    r=report()
    for field in ('feasible_native_policy_demonstrated','global_optimum_or_global_bound_claimed',
            'loss_or_selection_changed','native_rng_restored_or_simulation_resumed','publication_ready'):
        assert r[field] is False
    assert r['new_model_calls']==r['new_native_worlds']==0
    assert r['arithmetic_assumptions'] and r['not_a_global_bound_reasons']
