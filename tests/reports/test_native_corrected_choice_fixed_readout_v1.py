"""SCRIPTED 30 logical rows/60 contrasts; no actual native or unused evidence."""
from copy import deepcopy

import pytest

from scripts.reports import native_corrected_choice_fixed_evaluation_v1 as module
from scripts.reports import native_priority_fixed_evaluation_v1 as legacy_module
from scripts.native_corrected_choice_fixed_bank_v1 import freeze_bank, planned_jobs
from tests.reports.test_native_corrected_choice_fixed_bank_v1 import inputs
from tests.reports.test_native_priority_fixed_evaluation_readout_v1 import fixture as legacy_fixture, seal


def fixture(*, missing=False, failed=False):
    original, old_audit, slots, refs = inputs(null=missing)
    bank = freeze_bank(original, old_audit, slots, refs)
    jobs = planned_jobs(bank, deepcopy(module.SEEDS))['jobs']
    p, audit = legacy_fixture(failed=failed)
    assert p['losses'] == original['losses'] and len(jobs) == len(audit['worlds'])
    p.update(schema=module.STUDY + '.plan', fixed_selection=bank, jobs=jobs,
        origin_audit_content_sha256=old_audit['content_sha256']); p = seal(p)
    audit.update(schema=module.STUDY + '.audit', plan_sha256=p['content_sha256'],
        fixed_selection=deepcopy(bank), origin_audit_content_sha256=old_audit['content_sha256'])
    audit['worlds'] = [{**world, **deepcopy(job)} for world, job in zip(audit['worlds'], jobs)]
    return p, seal(audit)


def test_all_30_labels_and120_contrasts_preserve_origin_and_literal_sharing():
    p, a = fixture(); before = deepcopy((p, a)); result = module.summarize(p, a)
    assert (p, a) == before
    assert result['schema'] == module.SCHEMA and result['coverage']['logical_rows'] == 30
    assert result['coverage']['physical_worlds'] == 2
    assert len(result['contrast_definitions']) == 60 and len(result['fixed_policy_contrasts']) == 120
    assert len({row['id'] for row in result['contrast_definitions']}) == 60
    returned = [row for row in result['logical_rows'] if row.get('selection_scope') == 'best-known']
    own = [row for row in result['logical_rows'] if row.get('selection_scope') == 'own-only']
    assert len(returned) == len(own) == 12
    assert all(row['selected_origin'] == 'reference' for row in returned)
    assert all(row['selected_origin'] == 'own' for row in own)
    assert all(row['same_physical_job'] and all(v == 0 for v in row['differences'].values())
        for row in result['fixed_policy_contrasts'])
    assert not result['selection_changed'] and not result['method_superiority_claimed']
    with pytest.raises(ValueError): legacy_module.summarize(p, a)


def test_missing_own_scope_remains_absent_while_returned_reference_is_available():
    p, a = fixture(missing=True); result = module.summarize(p, a)
    assert result['coverage']['logical_rows'] == 30 and result['coverage']['selection_unavailable_rows'] == 2
    absent = [row for row in result['logical_rows'] if not row['selection_available']]
    assert all(row['selection_scope'] == 'own-only' and row['selected_origin'] is None
        and row['physical_job'] is None and all(v is None for v in row['scores'].values()) for row in absent)
    for row in result['fixed_policy_contrasts']:
        if row['right'] in result['missing_own_selections'] or row['left'] in result['missing_own_selections']:
            assert all(v is None for v in row['differences'].values())


def test_failed_world_preserves_all_shared_logical_nulls_and_missing_pair_conditions():
    p, a = fixture(failed=True); result = module.summarize(p, a)
    assert result['coverage']['failed_physical_worlds'] == 1
    assert sum(row['status'] == 'failed' for row in result['logical_rows']) == 15
    assert all(all(v is None for v in row['differences'].values()) for row in result['fixed_policy_contrasts']
        if row['seed'] == module.SEEDS[1])
    assert all(score['available_pairs'] == 1 and score['missing_seeds'] == [module.SEEDS[1]]
        for row in result['descriptive_contrast_summaries'] for score in row['scores'].values())


@pytest.mark.parametrize('problem', ['schema', 'job-label', 'origin-label', 'reselection', 'seed'])
def test_changed_or_mislabeled_scientific_inputs_rejected(problem):
    p, a = fixture()
    if problem == 'schema': p['schema'] = legacy_module.STUDY + '.plan'
    elif problem == 'job-label': p['jobs'][0]['labels'].pop()
    elif problem == 'origin-label':
        p['fixed_selection']['entries'][3]['selected_origin'] = 'own'
        p['fixed_selection'] = seal(p['fixed_selection']); a['fixed_selection'] = deepcopy(p['fixed_selection'])
    elif problem == 'reselection': p['claims']['candidate_reselection'] = True
    else: p['evaluation']['seeds'][0] += 2
    p = seal(p); a['plan_sha256'] = p['content_sha256']; a = seal(a)
    with pytest.raises(ValueError): module.summarize(p, a)
