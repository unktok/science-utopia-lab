"""Hash-verified native checkpoint extraction, not invented numerical dynamics."""
from dataclasses import asdict
from pathlib import Path

from utopia.optimization.loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.optimization.native_code_trace import recorded_contexts
from utopia.optimization.native_transition_autograd import NativeBinding, NativeTrajectory, DeclaredLinearTerminalLoss
from utopia.runtime.checkpointing import read_portable_checkpoint, pack_state
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import sha
from utopia.system.native_kernel import NativeScienceKernel, _json
from utopia.utils.data_utils import file_sha256

STATE_NAMES = ('native.accepted_decisions', 'native.rejected_decisions', 'native.review_records',
    'native.final_active_authors', 'native.final_author_resources', 'native.institutional_context_deliveries')
FEATURE_SCHEMA = {'schema': 'scienceutopia.native-transition-features.v1', 'names': STATE_NAMES,
    'semantics': 'actual cumulative decision/review counts, current authors/resources and delivered contexts at native year boundaries',
    'limitation': 'observed feature projection, not a sufficient Markov state for arbitrary researcher histories/text'}


def state_features(state):
    rounds = [r for p in state['paper_tracker']['papers'] for r in p['review_history']]
    authors = [a for a in state['ecosystem_data']['agents'] if a['can_author']]
    return (sum(r['decision'] == 'accept' for r in rounds), sum(r['decision'] == 'reject' for r in rounds),
        sum(len(r['reviews']) for r in rounds), sum(a['is_active'] for a in authors), sum(a['resources'] for a in authors),
        sum(e['event_type'] == 'native.system.context_delivered' for e in state['native_system']['events']))


def physical_initial_identity(state):
    fields = ('ecosystem_data', 'conference_system', 'citation_tracker', 'agent_tracker', 'funding_tracker',
        'paper_tracker', 'yearly_results', 'industry_funding_system', 'submitted_paper_ids',
        'initial_university_count', 'initial_industry_count', 'project_cost_policy', 'resource_ledger')
    document = {k: state[k] for k in fields if k in state}
    document['agent_states'] = state['portable']['agent_states']
    document['rng'] = state['portable']['rng']
    # Exclude design-dependent contracts and non-scientific cache/path/clocks.
    # Full checkpoints retain all omitted fields for independent inspection.
    # Trusted portable codec preserves actual ResearchDirection/FundingProgram
    # objects and aliases; JSON projection would silently drop domain state.
    return sha(pack_state(document))


def compile_terminal_loss(spec):
    validate_loss_spec(spec)
    if spec['across_seeds']['minimum_valid_runs'] != 1:
        raise ValueError('this native transition representation is a one-development-seed probe')
    weights = [0.] * len(STATE_NAMES)
    for term in spec['per_run']['terms']:
        if term['metric_id'] not in STATE_NAMES or term['slice_id'] is not None:
            raise ValueError('no tensor terminal adapter for declared native metric/slice')
        weights[STATE_NAMES.index(term['metric_id'])] += term['coefficient']
    return DeclaredLinearTerminalLoss(spec['id'], loss_spec_sha256(spec), STATE_NAMES, tuple(weights), spec['per_run']['intercept'])


def extract_trajectory(record, *, run_directory, source_commit, model_digest, corpus_sha256, controls, loss_spec):
    from utopia.optimization.native_feedback import checked_native_state
    if record['observation']['status'] != 'complete' or len(record['observation']['metadata']['runs']) != 1:
        raise ValueError('one complete actual native run required for transition extraction')
    run = record['observation']['metadata']['runs'][0]
    final, kernel = checked_native_state(record, run)
    spec = SystemSpec.from_dict(record['suggestion']['candidate'])
    node = next(n for n in spec.mechanisms if n.mechanism_id == 'world.selection')
    if node.parameters.get('annual_rates') != list(controls):
        raise ValueError('declared controls differ from actually installed native annual rates')
    root = Path(run_directory) / run['run_id']
    rows = recorded_contexts(root / 'code-contexts.jsonl', artifact=node.parameters['code_artifact'],
        binding={'source_commit': source_commit, 'system_fingerprint': spec.fingerprint, 'run_id': run['run_id']})
    call_evidence = []
    for year, rate in enumerate(controls, 1):
        matches = [r for r in rows if r['context']['period'] == year and r['context']['parameters']['annual_rates'] == list(controls)
            and any(e.event_type == 'generated.code_executed' and e.year == year and e.provenance['mechanism_id'] == 'world.selection'
                and e.payload['context_sha256'] == r['receipt']['context_sha256'] and e.payload['result_sha256'] == r['receipt']['result_sha256'] for e in kernel.events)]
        if not matches:
            raise ValueError('control value has no actual persisted native code execution')
        row = matches[-1]
        decisions = [m['payload'] for m in row['result']['outputs']['decisions'] if not m['payload'].get('empty_cycle')]
        call_evidence.append({'year': year, 'actual_rate': rate, 'context_sha256': row['receipt']['context_sha256'],
            'submitted_papers': len(decisions), 'accepted_paper_ids': [d['paper_id'] for d in decisions if d['decision'] == 'accept'],
            'bundle_sha256': row['bundle_sha256']})
    states, hashes, initial_identity = [], [], None
    for year in range(len(controls) + 1):
        path = Path(run['checkpoint_path']).parent / f'portable_checkpoint_year_{year}.json.gz'
        state = read_portable_checkpoint(path)
        contract = state['portable']['contract']['binding']
        if contract['cell'] != spec.fingerprint or contract['model_revision'] != model_digest or contract['corpus_sha256'] != corpus_sha256 or contract['science_config']['source_commit'] != source_commit:
            raise ValueError('native transition checkpoint source/model/corpus/system binding mismatch')
        restored = NativeScienceKernel(spec, checkpoint=state['native_system'])
        if restored.last_year != year:
            raise ValueError('native transition checkpoint completed year mismatch')
        if year == 0:
            initial_identity = physical_initial_identity(state)
        states.append(tuple(float(v) for v in state_features(state)))
        hashes.append(file_sha256(path))
    metrics = {name: {'status': 'measured', 'value': value} for name, value in zip(STATE_NAMES, states[-1])}
    measured = {'run_id': run['run_id'], 'system_fingerprint': spec.fingerprint,
        'measurement_schema': 'scienceutopia.native-domain-measurements.v1', 'metrics': metrics}
    evaluated = evaluate_loss(loss_spec, [measured])
    if evaluated != record['observation']['metadata']['loss_evaluation'] or evaluated['loss'] != record['observation']['loss']:
        raise ValueError('transition features do not reproduce exact native LossSpec evaluation')
    structural = spec.to_dict()
    next(n for n in structural['mechanisms'] if n['mechanism_id'] == 'world.selection')['parameters'].pop('annual_rates')
    common_world = sha({'initial_physical_state': initial_identity, 'common_implementation_graph': structural})
    binding = NativeBinding(source_commit, model_digest, corpus_sha256, common_world, sha(FEATURE_SCHEMA), STATE_NAMES, ('annual_selection_rate',))
    trajectory = NativeTrajectory(run['run_id'], binding, tuple(states), tuple((float(x),) for x in controls), tuple(hashes), evaluated['loss'])
    trajectory.validate(binding, compile_terminal_loss(loss_spec))
    return trajectory, {'run_id': run['run_id'], 'system_fingerprint': spec.fingerprint,
        'common_structure_sha256': sha(structural), 'initial_physical_state_sha256': initial_identity,
        'checkpoints': hashes, 'actual_control_executions': call_evidence}
