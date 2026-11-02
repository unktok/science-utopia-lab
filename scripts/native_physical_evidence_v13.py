"""V13 physical evidence adapter; old v7/v12 auditors remain unchanged."""
from pathlib import Path
import json

from scripts.analyze_native_open_v7 import (
    FIXTURE, RESPONSE_ACTUAL, read_portable_checkpoint, NativeScienceKernel,
    checkpoint_measurements, response_proofs, code_proofs, validate_record,
    derivative_diagnostics, joint_engineering_loss, domain_proofs,
    context_input_proofs, physical_initial_identity, SystemSpec, file_sha256, read,
)
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest

def audit_native_run_v13(root, draw, observation, evidence, world, classification, *,
        expected_experiment=None, expected_loss=None):
    """V7 evidence rules with lawful zero-code worlds explicitly supported.

    The old auditor remains byte-unchanged. All imported primitives and native
    runtime are bound to the actual source pin by the v13 caller.
    """
    expected_experiment = (expected_experiment if expected_experiment is not None else
        {'protocol': 'native-open-integrated-v7', 'role': 'development-engineering'})
    loss_spec = expected_loss if expected_loss is not None else joint_engineering_loss()
    system = SystemSpec.from_dict(draw['suggestion']['candidate'])
    checkpoint = Path(evidence['checkpoint_path']).resolve()
    cell = Path(root) / 'worlds' / evidence['run_id']
    if not checkpoint.is_relative_to(cell.resolve()) or file_sha256(checkpoint) != evidence['checkpoint_sha256']:
        raise ValueError('native checkpoint escapes physical run or file hash changed')
    saved = read_portable_checkpoint(checkpoint)
    binding = saved['portable']['contract']['binding']
    if (saved['portable']['contract']['native_system']['system_fingerprint'] != system.fingerprint
            or binding['cell'] != system.fingerprint or binding['seed'] != 42
            or binding['science_config']['source_commit'] != world['source_commit']
            or binding['model_revision'] != world['model_digest'] or binding['corpus_sha256'] != world['corpus_sha256']
            or saved['portable']['contract']['model'] != binding['model']
            or saved['portable']['contract']['model_revision'] != binding['model_revision']
            or binding['science_config']['years'] != saved['year']
            or (classification != FIXTURE and saved['year'] != 2)):
        raise ValueError('actual source/model/corpus/seed/design/native horizon differs')
    if classification != FIXTURE and (binding['model'] != 'qwen3:8b'
            or binding['science_config']['runtime_seed_binding'] != world['runtime_seed_binding']
            or binding['science_config']['experiment'] != expected_experiment
            or binding['science_config']['population'] != {'institutions': 5, 'per_institution': 1, 'strategy': 'balanced'}
            or binding['science_config']['corpus_years'] != 4
            or binding['science_config']['thinking_override'] is not False
            or binding['science_config']['max_tokens'] != 768
            or saved['rag']['ordered_documents_sha256'] != world['corpus_sha256']):
        raise ValueError('actual fixed-Qwen / original five-researcher corpus protocol differs')
    if read(cell / 'system.json') != system.to_dict():
        raise ValueError('physical source SystemSpec is not the evaluated generated candidate')
    kernel = NativeScienceKernel(system, checkpoint=saved['native_system'])
    if kernel.design_history:
        raise ValueError('fresh-world draw unexpectedly contains same-society migrations')
    measurement = checkpoint_measurements(checkpoint, evidence['run_id'], system.fingerprint)
    if evidence['event_stream_hash'] != kernel.to_dict()['event_stream_hash']:
        raise ValueError('observation event stream differs from restored actual native kernel')
    years = saved['year']
    counts, annual, previous_events, previous_elapsed = [], [], [], 0.
    for year in range(1, years + 1):
        annual_path = checkpoint.parent / f'portable_checkpoint_year_{year}.json.gz'
        state = read_portable_checkpoint(annual_path)
        if (state['year'] != year or state['phase'] != 5 or state['portable']['contract']['binding'] != binding
                or state['native_system']['spec'] != system.to_dict()):
            raise ValueError('annual checkpoint source/physical lineage differs')
        annual_kernel = NativeScienceKernel(system, checkpoint=state['native_system'])
        events = state['native_system']['events']
        if (events[:len(previous_events)] != previous_events or saved['native_system']['events'][:len(events)] != events):
            raise ValueError('native event lineage was reset or changed across annual checkpoints')
        elapsed = state['portable']['llm_call_stats'].get('elapsed_seconds', 0.)
        if elapsed < previous_elapsed:
            raise ValueError('annual native LLM elapsed counter rewound')
        annual.append({'year': year, 'checkpoint_sha256': file_sha256(annual_path),
            'accepted_decisions': sum(d.get('decision') == 'accept' for p in state['paper_tracker']['papers'] for d in p['review_history']),
            'context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in annual_kernel.events),
            'cumulative_responses': state['portable']['response_cache_count'],
            'llm_call_stats': state['portable']['llm_call_stats'], 'interval_llm_elapsed_seconds': elapsed-previous_elapsed,
            'native_event_stream_hash': state['native_system']['event_stream_hash']})
        previous_events, previous_elapsed = events, elapsed
        counts.append(state['portable']['response_cache_count'])
    response = response_proofs(cell, binding, counts, complete=True, protocol={},
        classification=RESPONSE_ACTUAL if classification != FIXTURE else FIXTURE)
    if any(int(y) > years for y in response['responses_by_physical_year']):
        raise ValueError('physical HTTP year exceeds actual native horizon')
    code = code_proofs(cell, system, saved['native_system'], world, evidence['run_id'], complete=True)
    code_path = cell / 'code-contexts.jsonl'
    code_rows = [validate_record(json.loads(line)) for line in code_path.read_text().splitlines()] if code_path.exists() else []
    initial = read_portable_checkpoint(checkpoint.parent / 'portable_checkpoint_year_0.json.gz')
    if (initial['year'] != 0 or initial['phase'] != 0 or initial['portable']['response_cache_count'] != 0
            or initial['native_system']['events'] or initial['native_system']['last_year'] != 0
            or initial['native_system']['spec'] != system.to_dict()
            or initial['portable']['contract']['binding'] != binding):
        raise ValueError('native draw lacks its original initialized candidate world')
    initial_authors = [a for a in initial['ecosystem_data']['agents'] if a['can_author']]
    NativeScienceKernel(system, checkpoint=initial['native_system'])
    if classification != FIXTURE and len(initial_authors) != 5:
        raise ValueError('actual original initialized population is not five researchers')
    coverage, backward = derivative_diagnostics(system, kernel.events)
    conditional_scope = ('Minus represented router actions, conditioned on recorded numeric inputs; '
        'NOT joint LossSpec -A-0.1C or full native/LLM pathwise derivative.' if loss_spec == joint_engineering_loss()
        else 'Minus represented router actions, conditioned on recorded numeric inputs; '
            'NOT the bound native LossSpec or full native/LLM pathwise derivative.')
    return {'measurement': measurement, 'native_loss': evaluate_loss(loss_spec, [measurement])['loss'],
        'physical_initial_identity': physical_initial_identity(initial),
        'response_proof': response, 'code_proof': code, 'native_counts': domain_proofs(saved, kernel, code_rows),
        'context_input_proof': context_input_proofs(cell, saved),
        'annual_checkpoints': annual,
        'boundary_coverage': coverage, 'conditional_backward': backward,
        'checkpoint_sha256': file_sha256(checkpoint), 'actual_author_count': len([a for a in saved['ecosystem_data']['agents'] if a['can_author']]),
        'initial_roster': {'author_count': len(initial_authors), 'total_actor_count': len(initial['ecosystem_data']['agents']),
            'actor_ids_sha256': digest(sorted(a['id'] for a in initial['ecosystem_data']['agents'])),
            'actual_conference_count': len(initial['conference_system']['conferences']),
            'configured_num_conferences': 1 if classification != FIXTURE else None,
            'note': 'Configured count and actual per-category conference instances are separate facts.'},
        'conditional_backward_scope': conditional_scope}
