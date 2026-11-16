"""Pure transfer of all frozen mixed-study policies to a future evaluation.

This is not a dispatchable evaluation plan, seed-usage proof or cold audit.
Only literal programs modulo the explicitly rebound world seed may share jobs.
"""
from scripts.native_design_benchmark_plan import policy_identity
from scripts.reports.native_priority_method_readout_v1 import analyze, METHODS, OBJECTIVES, SCHEMA as LEGACY_READOUT
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-priority-fixed-bank.v1'


def seal(value):
    return {**value, 'content_sha256': digest(value)}


def selection_label(method, history, objective):
    return 'selected/' + method + '/history-' + str(history) + '/' + objective


def freeze_bank(plan, audit, slots, references):
    # The same all-slot projection verifies every audited world, generation
    # failure, assigned loss, earliest own tie and literal selected program.
    report = analyze(plan, audit, slots, references)
    if report['schema'] != LEGACY_READOUT:
        raise ValueError('legacy own-only bank cannot label corrected best-known references as own discoveries')
    visible = [r for r in report['references'] if r['visible_parent']]
    selected = []
    for row in report['selected']:
        method, history, objective = row['method'], row['replication'], row['objective']
        original = audit['selection']['selected'][method][str(history)][objective]
        selected.append({'label': selection_label(method, history, objective),
            'role': 'own-selection', 'method': method, 'optimizer_history': history, 'objective': objective,
            'selected_cell_id': row['cell_id'], 'selected_id': row['suggestion_id'],
            'development_loss': row['loss'], 'completed_submissions': row['completed_submissions'],
            'development_cross_scores': clone(row['cross_scores']),
            'development_initial_reference_label': min(visible, key=lambda r: r['cross_scores'][objective])['label'],
            'development_initial_reference_loss': row['reference_loss'],
            'all_tied_ids': clone(row['all_tied_ids']), 'system': clone(original['system']),
            'selection_available': original['system'] is not None})
    refs = [{'label': 'reference/' + label, 'role': 'reference', 'reference_label': label,
        'system': clone(references[label]['candidate']), 'selection_available': True,
        'development_cross_scores': clone(report['references'][i]['cross_scores']),
        'optimizer_visible': report['references'][i]['visible_parent']}
        for i, label in enumerate(plan['reference_order'])]
    return seal({'schema': SCHEMA, 'scientific_source_commit': plan['source_commit'],
        'origin_plan_content_sha256': plan['content_sha256'], 'origin_audit_content_sha256': audit['content_sha256'],
        'origin_selection_content_sha256': audit['selection']['content_sha256'],
        'losses': clone(plan['losses']), 'reference_order': clone(plan['reference_order']),
        'development_world_seed': plan['initial_system']['initial_state']['seed'],
        'entries': refs + selected, 'missing_own_selections': [r['label'] for r in selected if not r['selection_available']],
        'candidate_reselection': False, 'reference_fallback': False, 'new_model_calls': 0,
        'new_native_worlds': 0, 'seed_usage_validated': False, 'dispatchable': False,
        'scope': 'Literal frozen policies only. No observed-input-class or AST-based coalescing. '
                 'Labels sharing a physical job are not independent replications. Original native world is retained.'})


def planned_jobs(bank, seeds):
    """A pure job draft, not a claim that seeds are unused or execution is ready."""
    checked(bank)
    if (bank['schema'] != SCHEMA or bank['candidate_reselection'] or bank['reference_fallback']
            or bank['dispatchable'] or bank['seed_usage_validated']
            or type(seeds) is not list or not 1 <= len(seeds) <= 3
            or any(type(s) is not int or not 0 <= s < 2**31 or s == bank['development_world_seed'] for s in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError('literal frozen bank and explicit finite non-development seed draft required')
    entries = bank['entries']; refs = entries[:3]; own = entries[3:]
    expected = [(m, h, o) for m in METHODS for h in range(2) for o in OBJECTIVES]
    if (len(refs) != 3 or len(own) != 12 or len({e['label'] for e in entries}) != 15
            or [e['role'] for e in refs] != ['reference'] * 3
            or [e['reference_label'] for e in refs] != bank['reference_order']
            or [e['label'] for e in refs] != ['reference/' + name for name in bank['reference_order']]
            or [(e['method'], e['optimizer_history'], e['objective']) for e in own] != expected
            or [e['label'] for e in own] != [selection_label(*key) for key in expected]
            or any(e['role'] != 'own-selection' for e in own)
            or any(e['selection_available'] != (e['system'] is not None) for e in entries)
            or any(e['system'] is None for e in refs)
            or [e['label'] for e in own if e['system'] is None] != bank['missing_own_selections']):
        raise ValueError('all three references and twelve ordered frozen own labels required, including absent selections')
    policies = {}
    for entry in entries:
        system = entry['system']
        if system is None: continue
        identity = policy_identity(system)
        policies.setdefault(identity, {'system': system, 'labels': []})['labels'].append(entry['label'])
    jobs = []
    for identity, policy in policies.items():
        for seed in seeds:
            system = clone(policy['system']); system['initial_state']['seed'] = seed
            if policy_identity(system) != identity: raise ValueError('world-seed binding changes policy')
            jobs.append({'identity': 'evaluation-' + str(len(jobs)).zfill(3), 'policy_sha256': identity,
                'seed': seed, 'labels': clone(policy['labels']), 'system': system})
    return seal({'schema': SCHEMA + '.job-draft', 'bank_content_sha256': bank['content_sha256'],
        'seeds': clone(seeds), 'jobs': jobs, 'logical_policy_labels': 15,
        'missing_own_selections': clone(bank['missing_own_selections']),
        'maximum_physical_worlds': 15 * len(seeds), 'planned_physical_worlds': len(jobs),
        'candidate_reselection': False, 'seed_usage_validated': False, 'dispatchable': False,
        'new_model_calls': 0, 'new_native_worlds': 0})
