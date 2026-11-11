"""Scripted record arithmetic, not native evidence or a causal paper matching."""
import pytest
from scripts.reports.native_content_overlap_v1 import overlap


def row(identity,score,year=1):
    return {'year':year,'paper_id':identity,'rating':{'status':'measured','content_sha256':identity,
        'ratings':[{'score':score} for _ in range(3)],'mean_score':float(score)}}


def test_net_two_records_is_not_two_added_papers_or_a_changed_objective():
    common=[row('s'+str(i),4) for i in range(3)]
    a=common+[row('a',3),row('b',3),row('c',4),row('d',3)]
    b=common+[row('e',4),row('f',3)]
    r=overlap(a,b)
    assert r['common']['occurrences']==3 and r['left_only']['occurrences']==4 and r['right_only']['occurrences']==2
    assert r['left']['occurrences']==7 and r['right']['occurrences']==5
    assert r['left']['score_sum']==25. and r['right']['score_sum']==19.
    assert r['left']['centered_utility_sum']==r['right']['centered_utility_sum']==4.
    assert r['conditional_center_indifference']=={'numerator':3,'denominator':1}
    assert r['left_minus_right']['utility_loss_at_declared_center_3']==0.


def test_multiplicity_year_and_content_are_not_deduplicated():
    r=overlap([row('same',4),row('same',4),row('same',4,year=2)],[row('same',4)])
    assert r['common']['occurrences']==1 and r['left_only']['occurrences']==2
    assert r['left']['records'][0]['multiplicity']==2
    assert overlap([row('same',3)],[row('other',4)])['conditional_center_indifference'] is None


def test_exact_three_position_fraction_and_inconsistent_cache_are_distinct():
    a=row('a',3);a['rating']['ratings'][-1]['score']=4;a['rating']['mean_score']=10/3
    r=overlap([a],[])
    assert r['left']['exact_score_sum']=={'numerator':10,'denominator':3}
    assert r['left']['exact_centered_utility_sum']=={'numerator':1,'denominator':3}
    with pytest.raises(ValueError):overlap([row('same',3)],[row('same',4)])


@pytest.mark.parametrize('bad',[True,None,6,-1])
def test_invalid_literal_rating_never_becomes_zero_utility(bad):
    a=row('a',3);a['rating']['ratings'][0]['score']=bad
    with pytest.raises(ValueError):overlap([a],[])


def test_actual_retained_export_and_figure_hashes_keep_stopped_reference_scope():
    import json
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    from utopia.utils.data_utils import file_sha256
    root=Path(__file__).resolve().parents[2]/'research/data/native-content-overlap-v1'
    report=checked(json.loads((root/'report.json').read_text()))
    manifest=checked(json.loads((root/'manifest.json').read_text()))
    assert all(file_sha256(root/name)==value for name,value in manifest['files'].items())
    assert report['content_sha256']==manifest['report_content_sha256']=='b6e993f61e7fed0502810e41091658b9326bd0ff1e8a20d87e5e0e2151abb271'
    assert report['scope']=='stopped-development-reference-diagnostic'
    assert not any(report[k] for k in ('loss_changed','selection_changed','causal_mediation_claimed','publication_ready'))
    r=report['overlap'];assert (r['common']['occurrences'],r['left_only']['occurrences'],r['right_only']['occurrences'])==(3,4,2)
    assert r['left']['centered_utility_sum']==r['right']['centered_utility_sum']==4.
