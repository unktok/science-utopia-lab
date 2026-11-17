"""Synthetic all-slot reader checks; not native institutional findings."""
from copy import deepcopy

import pytest

from scripts.reports import native_priority_method_readout_v1 as r
from tests.reports.test_native_priority_method_readout_v1 import fixture as old_fixture, seal


def fixture():
    p, a, slots, refs = old_fixture()
    mapping = {r.METHODS[0]:r.INFORMATION_METHODS[0], r.METHODS[2]:r.INFORMATION_METHODS[1]}
    chosen = [deepcopy(s) for s in slots if s['slot']['replication'] == 0 and s['slot']['method'] in mapping]
    for row in chosen: row['slot']['method'] = mapping[row['slot']['method']]
    worlds = [deepcopy(w) for w in a['worlds'] if w['role'] == 'developer-reference'
        or w['optimizer_history'] == 0 and w['method'] in mapping]
    for w in worlds:
        if w['role'] == 'developer-reference': continue
        w.update(method=mapping[w['method']], role='workflow-own-proposal')
    p = r.literal(p)
    p.update(schema=r.INFORMATION_STUDY+'.plan', methods=list(r.INFORMATION_METHODS),
        protocol='research/protocols/campaigns/native-literal-feedback-comparison-v1.md',
        replication_seeds=[79011], schedule=[deepcopy(s['slot']) for s in chosen],
        literal_feedback_contract={'scope':'parent-relative-literal-design-change-v1'})
    p = seal(p)
    banks = {key:{'0':deepcopy(a['selection']['selected'][old]['0'])} for old,key in mapping.items()}
    for by_history in banks.values():
        for endpoint in by_history['0'].values(): endpoint['selected_origin'] = 'own'
    selection = seal({'selected':deepcopy(banks), 'own_only_selected':deepcopy(banks),
        'primary_is_measured_best_known_not_own_discovery':True,
        'baseline_fallback':False, 'held_out_evaluation':False})
    a = r.literal(a)
    a.update(schema=r.INFORMATION_STUDY+'.audit', plan_sha256=p['content_sha256'],
        worlds=worlds, selection=selection,
        closure={'terminal':{'status':'closed','consumed_slots':8,'observations':11}})
    return p, seal(a), chosen, refs


def test_all_eight_free_information_slots_keep_both_exact_endpoints_and_full_paths():
    p, a, slots, refs = fixture(); result = r.analyze(p,a,slots,refs)
    assert result['schema'] == r.INFORMATION_SCHEMA
    assert result['coverage']['declared_own_slots'] == result['coverage']['complete_own_slots'] == 8
    assert result['coverage']['physical_worlds'] == 11
    assert len(result['selected']) == len(result['own_only_selected']) == len(result['paths']) == 4
    assert all(len(path) == 2 for path in result['paths'].values())
    assert all(row['selected_origin'] == 'own' for row in result['selected'])
    assert not result['selection_changed'] and not result['method_superiority_claimed']
    assert result['information_contract'] == p['literal_feedback_contract']
    assert 'not independent replication' in result['interpretation']


@pytest.mark.parametrize('error', ['drop-slot','numeric-role','wrong-arm','wrong-protocol','wrong-contract','wrong-primary'])
def test_information_profile_does_not_relax_compound_identity_or_frozen_selection(error):
    p, a, slots, refs = fixture()
    if error == 'drop-slot': slots.pop()
    elif error == 'numeric-role': a['worlds'][3]['role'] = 'numeric-own-proposal'
    elif error == 'wrong-arm': a['worlds'][3]['method'] = 'invented-third-arm'
    elif error == 'wrong-protocol': p['protocol'] = 'historical-protocol'
    elif error == 'wrong-contract': p['literal_feedback_contract']['scope'] = 'unknown'
    else: a['selection']['selected'][r.INFORMATION_METHODS[0]]['0'][r.OBJECTIVES[0]]['selected_origin'] = 'reference'
    p = seal(r.literal(p)); a['plan_sha256'] = p['content_sha256']; a = seal(r.literal(a))
    with pytest.raises(ValueError): r.analyze(p,a,slots,refs)
