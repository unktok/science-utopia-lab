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
