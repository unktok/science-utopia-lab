"""SCRIPTED all-label transfer; no unused seed claim, native job or inference."""
from copy import deepcopy

import pytest

from scripts import native_priority_fixed_bank_v1 as module
from tests.reports.test_native_priority_method_readout_v1 import fixture, seal
from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES


def inputs():
    p, a, slots, refs = fixture()
    # Supply explicit world binding to every literal fixture program. The
    # fixture is synthetic data, never a validated native SystemSpec.
    for s in slots:
        for system in (s['suggestion']['candidate'], s['observation']['candidate'], s['parent_system']):
            system['initial_state'] = {'seed': 61001}
    for ref in refs.values(): ref['candidate']['initial_state'] = {'seed': 61001}
    for world in a['worlds']: world['system']['initial_state'] = {'seed': 61001}
    for method in a['selection']['selected'].values():
        for history in method.values():
            for entry in history.values(): entry['system']['initial_state'] = {'seed': 61001}
    p['initial_system'] = deepcopy(refs['zero']['candidate'])
    p = seal({k: v for k, v in p.items() if k != 'content_sha256'})
    a['plan_sha256'] = p['content_sha256']
    a['selection'] = seal({k: v for k, v in a['selection'].items() if k != 'content_sha256'})
    a = seal({k: v for k, v in a.items() if k != 'content_sha256'})
    return p, a, slots, refs


def test_all_fifteen_labels_survive_exact_policy_sharing_without_worlds():
    args = inputs(); bank = module.freeze_bank(*args)
    assert len(bank['entries']) == 15 and not bank['missing_own_selections']
    assert bank['origin_selection_content_sha256'] == args[1]['selection']['content_sha256']
    before = deepcopy(bank); draft = module.planned_jobs(bank, [83003, 83011])
    assert bank == before and draft['planned_physical_worlds'] == 2
    assert all(len(j['labels']) == 15 for j in draft['jobs'])
    assert [j['seed'] for j in draft['jobs']] == [83003, 83011]
    assert not draft['dispatchable'] and not draft['seed_usage_validated']
    assert draft['new_model_calls'] == draft['new_native_worlds'] == 0


def test_source_or_parameter_difference_never_coalesces_on_equal_development_scores():
    p, a, slots, refs = inputs()
    target = (METHODS[0], 0, OBJECTIVES[0]); program = {'unused_parameter': 'literal difference remains'}
    for entry in slots:
        s = entry['slot']
        if (s['method'], s['replication'], s['objective']) == target:
            entry['suggestion']['candidate']['extra'] = deepcopy(program)
            entry['observation']['candidate']['extra'] = deepcopy(program)
    for world in a['worlds']:
        if (world.get('method'), world.get('optimizer_history'), world.get('objective')) == target:
            world['system']['extra'] = deepcopy(program)
    a['selection']['selected'][target[0]]['0'][target[2]]['system']['extra'] = deepcopy(program)
    a['selection'] = seal({k: v for k, v in a['selection'].items() if k != 'content_sha256'})
    a = seal({k: v for k, v in a.items() if k != 'content_sha256'})
    draft = module.planned_jobs(module.freeze_bank(p, a, slots, refs), [83003])
    assert draft['planned_physical_worlds'] == 2
    assert sorted(len(j['labels']) for j in draft['jobs']) == [1, 14]


@pytest.mark.parametrize('seeds', [[], [61001], [True], [-1], [2**31], [83003, 83003], [1, 2, 3, 4]])
def test_invalid_or_development_seed_drafts_rejected(seeds):
    bank = module.freeze_bank(*inputs())
    with pytest.raises(ValueError): module.planned_jobs(bank, seeds)


def test_no_own_selection_stays_absent_not_a_reference_fallback():
    p, a, slots, refs = inputs(); target = (METHODS[2], 0, OBJECTIVES[0])
    for entry in slots:
        s = entry['slot']
        if (s['method'], s['replication'], s['objective']) == target:
            entry.update(suggestion=None, observation=None, generation_error={'SCRIPTED': 'generation failure'})
    a['worlds'] = [w for w in a['worlds'] if (w.get('method'), w.get('optimizer_history'), w.get('objective')) != target]
    a['closure']['terminal']['observations'] = 25
    a['selection']['selected'][target[0]]['0'][target[2]] = {'loss': None, 'completed_submissions': 0,
        'all_tied_ids': [], 'selected_id': None, 'system': None, 'reference_loss': -10.}
    a['selection'] = seal({k: v for k, v in a['selection'].items() if k != 'content_sha256'})
    a = seal({k: v for k, v in a.items() if k != 'content_sha256'})
    bank = module.freeze_bank(p, a, slots, refs); draft = module.planned_jobs(bank, [83003])
    assert len(bank['entries']) == 15 and len(bank['missing_own_selections']) == 1
    assert draft['missing_own_selections'] == bank['missing_own_selections']
    assert len(draft['jobs'][0]['labels']) == 14


@pytest.mark.parametrize('edit', ['dropped-label', 'reordered-label', 'reference-fallback', 'fabricated-unused'])
def test_draft_refuses_lost_labels_or_unearned_execution_claim(edit):
    bank = module.freeze_bank(*inputs())
    if edit == 'dropped-label': bank['entries'].pop()
    elif edit == 'reordered-label': bank['entries'][-1], bank['entries'][-2] = bank['entries'][-2], bank['entries'][-1]
    elif edit == 'reference-fallback': bank['reference_fallback'] = True
    else: bank['seed_usage_validated'] = True
    bank = seal({k: v for k, v in bank.items() if k != 'content_sha256'})
    with pytest.raises(ValueError): module.planned_jobs(bank, [83003])
