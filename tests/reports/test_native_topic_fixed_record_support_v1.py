"""Reconstruct exact fixed-record diagnostics; no critic, world or new loss."""
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]


def test_retained_original_ratings_and_all_fixed_record_signs_reconstruct():
    diagnostic=json.loads((ROOT/'research/results/native-topic-fixed-record-support-v1.json').read_text())
    source=ROOT/diagnostic['input_report']
    assert file_sha256(source)==diagnostic['input_report_file_sha256']
    original=checked(json.loads(source.read_text()))
    assert original['content_sha256']==diagnostic['input_report_content_sha256']
    assert original['scientific_source_commit']==diagnostic['scientific_source_commit']
    assert len(original['worlds'])==len(diagnostic['rows'])==2
    for world,row in zip(original['worlds'],diagnostic['rows']):
        assert world['condition']==row['condition']
        contributions=[]; literal=[]
        for record in world['accepted_content']:
            rating=record['rating']; values=[r['score'] for r in rating['ratings']]
            assert rating['status']=='measured' and len(values)==3
            assert all(type(v) is int and 1<=v<=5 for v in values)
            assert rating['mean_score']==sum(values)/3
            contributions.append(Fraction(sum(values)-9,3))
            literal.append(rating['mean_score']-3)
        assert dict(Counter(str(v) for v in contributions))==row['rational_contribution_histogram']
        total=sum(contributions,Fraction(0))
        assert row['rational_utility_sum_diagnostic']=={'numerator':total.numerator,'denominator':total.denominator}
        assert row['accepted_occurrences']==len(contributions)
        assert row['positive']==sum(v>0 for v in contributions)
        assert row['zero']==sum(v==0 for v in contributions)
        assert row['negative']==sum(v<0 for v in contributions)==0
        assert row['original_mean_score_utility_sum']==math.fsum(literal)==-world['scores']['content-utility']
        assert row['original_recorded_utility_loss']==world['scores']['content-utility']
        # Exact rational transcription is diagnostic, not replacement loss.
        assert math.isclose(float(total),math.fsum(literal),rel_tol=0,abs_tol=5e-15)
        assert row['fixed_record_count_optimal_acceptance_masks']==1
        assert row['fixed_record_utility_optimal_acceptance_masks']==2**row['zero']
        assert row['collected_resource_cost_observed']==world['resource_cost']


def test_fixed_record_masks_are_not_claimed_as_worlds_or_optimized_institutions():
    r=json.loads((ROOT/'research/results/native-topic-fixed-record-support-v1.json').read_text())
    for flag in ('world_level_utility_optimality_proved','world_level_resource_optimality_proved',
        'critic_opinions_are_scientific_truth','native_world_replaced_by_arithmetic',
        'historical_losses_or_selections_changed','publication_ready'):
        assert r[flag] is False
    assert r['new_model_calls']==r['new_native_worlds']==0
    assert all(not row['fixed_record_utility_can_improve_by_rejecting_only'] for row in r['rows'])
    assert 'not simulated policies' in r['fixed_record_scope']
