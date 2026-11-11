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


def test_integrated_pdf_preserves_prior_snapshot_and_binds_actual_build_source():
    import hashlib
    import json
    from pathlib import Path
    import subprocess
    from utopia.utils.data_utils import file_sha256
    root=Path(__file__).resolve().parents[2]
    r=json.loads((root/'paper/integrated-content-overlap-build-v1.json').read_text())
    assert file_sha256(root/r['output'])==r['pdf_sha256']
    for name,value in r['preserved_files'].items():assert file_sha256(root/name)==value
    original=lambda name:subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=root)
    for name in ('source_files','figure_files','support_files','evidence_files'):
        values={p:hashlib.sha256(original(p)).hexdigest() for p in r[name]['files']}
        assert hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()==r[name]['manifest_sha256']
    assert (r['pages'],r['figures'],r['tables'])==(55,26,21)
    assert r['visual_review']['pages_reviewed_for_layout']==55 and r['build']['text_identical']
    assert r['build']['exit_codes']==[0,0] and r['build']['bbox_word_tags_accounted']==21457
    assert r['build']['off_page_text_words']==r['build']['unresolved_question_mark_pairs']==0
    assert not r['scientific_scope']['publication_ready'] and not r['scientific_scope']['ongoing_corrected_search_counted_as_completed']
    assert r['scientific_scope']['historical_completed_developer_references']==5
    assert file_sha256(root/'paper/figures/native-content-overlap-v1/content-overlap.png')==file_sha256(root/'research/data/native-content-overlap-v1/content-overlap.png')
