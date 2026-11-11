"""Preference arithmetic only; scripted numbers are not new native evidence."""
import pytest

from scripts.reports.native_objective_preference_geometry_v1 import geometry


def row(identity,a,b,seed=42,status='complete'):
    return {'identity':identity,'scores':{'T':a,'U':b},'seed':seed,'status':status}


def test_shared_chosen_point_can_hide_distinct_minimum_sets_without_strict_conflict():
    rows=[row('R0',-7.,-4.),row('R1',-7.,-4.),row('R2',-7.,-4.),row('R3',0.,0.),row('R4',-5.,-4.)]
    r=geometry(rows,['T','U'])['by_world_seed'][0];pair=r['objective_pairs'][0]
    assert r['observed_minima']['T']['all_tied_physical_ids']==['R0','R1','R2']
    assert r['observed_minima']['U']['all_tied_physical_ids']==['R0','R1','R2','R4']
    assert pair['pair_counts']=={'joint-tie':3,'same-strict-preference':4,'strict-conflict':0,'tie-only-first':0,'tie-only-second':3}
    assert not pair['observed_minimum_sets_equal'] and pair['observed_minimum_set_intersection']==['R0','R1','R2']
    assert r['observed_nondominated_physical_ids']==['R0','R1','R2']
    assert geometry(list(reversed(rows)),['T','U'])==geometry(rows,['T','U'])


def test_strict_conflicts_ties_nulls_and_seeds_are_not_mixed_or_imputed():
    rows=[row('a',-3.,-1.),row('b',-1.,-3.),row('c',-3.,None),row('d',-99.,-99.,status='failed'),row('e',-9.,-9.,seed=99)]
    r=geometry(rows,['T','U'])['by_world_seed'];assert len(r)==2
    assert r[0]['common_completed_ids']==['a','b'] and len(r[0]['excluded_from_common_geometry'])==2
    assert r[0]['objective_pairs'][0]['pair_counts']['strict-conflict']==1
    assert r[0]['objective_pairs'][0]['observed_minimum_set_intersection']==[]
    assert r[1]['observed_minima']['T']['loss']==-9. and not r[1]['objective_pairs'][0]['pairs']


def test_all_unavailable_does_not_acquire_a_best_policy_or_zero_loss():
    r=geometry([row('bad',None,None,status='failed')],['T','U'])['by_world_seed'][0]
    assert r['observed_minima']['T']=={'loss':None,'all_tied_physical_ids':[]}
    assert r['objective_pairs'][0]['observed_minimum_sets_equal'] is None


@pytest.mark.parametrize('rows',[[row('dup',1.,2.),row('dup',2.,1.)],[row('bad',True,1.)],
    [row('bad',float('nan'),1.)],[row('bad',1.,1.,seed=True)]])
def test_invalid_loss_or_duplicate_physical_identity_is_not_silently_deduplicated(rows):
    with pytest.raises(ValueError):geometry(rows,['T','U'])


def test_retained_stopped_reference_export_preserves_original_hashes_and_scope():
    import json
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    from utopia.utils.data_utils import file_sha256
    root=Path(__file__).resolve().parents[2]/'research/data/native-objective-initial-stop-v1'
    report=checked(json.loads((root/'preference-report.json').read_text()))
    manifest=checked(json.loads((root/'preference-manifest.json').read_text()))
    assert file_sha256(root/'preference-report.json')==manifest['report_file_sha256']=='5389bb7782e3acc575c4e62c86b9e825e91edadffd1bbb5e4bbb0749b4e846f7'
    assert report['content_sha256']==manifest['report_content_sha256']=='120f178c6b35384d95f09e08f36f7f674d259bea64f3f3c0baf35af8306ef999'
    assert report['scope']=='stopped-development-reference-diagnostic'
    assert not report['frozen_selection_changed'] and not report['publication_ready']
    assert report['new_model_calls']==report['new_code_executions']==0
    group,=report['geometry']['by_world_seed'];pair,=group['objective_pairs']
    assert group['seed']==61001 and group['common_completed_rows']==5
    assert len(group['observed_minima']['throughput']['all_tied_physical_ids'])==3
    assert len(group['observed_minima']['content-utility']['all_tied_physical_ids'])==4
    assert pair['pair_counts']['strict-conflict']==0 and pair['pair_counts']['tie-only-second']==3
