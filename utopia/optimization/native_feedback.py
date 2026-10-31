"""Result-conditioned source revision on the actual native world.

Host attachment is unchanged and explicitly NOT model-invented topology.
Free Python algorithms are authored by the model and executed only in Docker.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, validate_code_artifact
from utopia.system.design_patch import apply_design_patch, clone, digest, make_patch
from utopia.utils.data_utils import file_sha256, write_json_atomic


def checked_native_state(record, run):
    path = Path(run['checkpoint_path'])
    if file_sha256(path) != run['checkpoint_sha256']:
        raise ValueError('native feedback checkpoint hash mismatch')
    state = read_portable_checkpoint(path)
    from utopia.system.native_kernel import NativeScienceKernel
    spec = SystemSpec.from_dict(record['suggestion']['candidate'])
    kernel = NativeScienceKernel(spec, checkpoint=state['native_system'])
    if kernel.to_dict()['event_stream_hash'] != run['event_stream_hash']:
        raise ValueError('native feedback event identity mismatch')
    return state, kernel


def feedback_from_native_history(history):
    """Technical activity and actual scores, never fabricated success signals."""
    result = []
    for record in history:
        observation = record['observation']
        row = {'suggestion_id': record['suggestion']['suggestion_id'],
               'observation_id': observation['observation_id'],
               'status': observation['status'], 'loss': observation['loss'],
               'measurements': clone(observation['metadata']['measurements']),
               'technical_failures': clone(observation['metadata']['technical_failures']),
               'executions': [], 'changed_implementations': []}
        spec = SystemSpec.from_dict(record['suggestion']['candidate'])
        changed = set(record['difference']['nodes_added'] + record['difference']['nodes_changed'])
        for node in spec.mechanisms:
            if node.mechanism_id in changed and node.implementation == CODE_IMPLEMENTATION:
                row['changed_implementations'].append({'id': node.mechanism_id, 'artifact': clone(node.parameters['code_artifact'])})
        for run in observation['metadata']['runs']:
            state, kernel = checked_native_state(record, run)
            counts = Counter((e.provenance.get('mechanism_id'), e.event_type) for e in kernel.events)
            paper_counts = Counter()
            for paper in state['paper_tracker']['papers']:
                ids = paper.get('author_id', [])
                for author in ([ids] if isinstance(ids, str) else ids):
                    paper_counts[author] += 1
            row['executions'].append({'seed': run['seed'], 'completed_year': kernel.last_year,
                'checkpoint_sha256': run['checkpoint_sha256'],
                'mechanism_event_counts': [{'mechanism': node, 'event': event, 'count': count}
                    for (node, event), count in sorted(counts.items(), key=lambda x: str(x[0]))],
                'delivered_messages': [clone(e.payload['message']) for e in kernel.events
                    if e.event_type == 'native.system.context_delivered'],
                'authors': [{key: a.get(key) for key in ('id', 'resources', 'is_active')}
                    for a in state['ecosystem_data']['agents'] if a.get('can_author')],
                'observed_papers': [{key: p.get(key) for key in ('id', 'author_id', 'title', 'review_history')}
                    for p in state['paper_tracker']['papers'][:24]],
                'observed_paper_records_per_author': dict(paper_counts),
                'observation_scope': 'completed native checkpoint; at most first 24 real paper records, not invented examples'})
        result.append(row)
    return {'schema': 'scienceutopia.native-design-feedback.v1', 'observations': result,
            'interpretation': 'actual losses and activity; activity is not a hidden objective or validity floor'}


class NativeSourceRevisionProposer:
    """Revise an existing free-source mechanism from genuine runtime feedback.

    Source algorithms and JSON memory are free; ports/wiring are held fixed on
    this route. The separate native graph-intent proposer retains graph freedom.
    Valid inert proposals are never rejected on behavioral grounds.
    """
    def __init__(self, model, executor, *, node_id, receipts, instructions='', max_attempts=3, planning=False):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError('bounded technical repair budget required')
        self.model, self.executor, self.node_id = model, executor, node_id
        self.receipts, self.instructions, self.max_attempts = Path(receipts), instructions, max_attempts
        self.planning = planning

    def __call__(self, parent, history, index, loss_spec):
        node_index = next(i for i, n in enumerate(parent.mechanisms) if n.mechanism_id == self.node_id)
        node = parent.mechanisms[node_index]
        if node.implementation != CODE_IMPLEMENTATION or {p.port_id for p in node.inputs} != {'observations'} or {p.port_id for p in node.outputs} != {'messages'}:
            raise ValueError('source-revision route requires an existing observation/messages Python institution')
        feedback = feedback_from_native_history(history)
        latest = next((r for r in reversed(history) if r['observation']['metadata']['runs']), None)
        if latest is None:
            raise ValueError('actual native checkpoint required for source revision')
        state, _ = checked_native_state(latest, latest['observation']['metadata']['runs'][0])
        world = {'year': state['native_system']['last_year'], 'ecosystem': state['ecosystem_data'],
                 'papers': state['paper_tracker'], 'conferences': state['conference_system'],
                 'year_results': state['yearly_results'][-1]}
        # Checkpoint year is authoritative in kernel state; codec current_year
        # can mean the next coordinator cursor and must not be guessed.
        world['year'] = state['native_system']['last_year']
        prompt = ('Revise this institutional Python algorithm using actual native execution feedback. '
            'The original researcher LLM weights/personas and world equations remain unchanged. '
            'This route preserves ports and wiring; implementation logic and JSON memory are yours to design. '
            'Return exactly {label,source,rationale}. source defines def step(context), standard library only. '
            "world=context['inputs']['observations'][0]['payload']; world contains year, "
            'ecosystem.agents (id,can_author,resources,is_active), papers.papers (id,title,author_id,review_history). '
            "Old memory=context['state']; parameters=context['parameters']. "
            "Return {'outputs':{'messages':[{'payload':{YOUR_FIELDS},'actor_ids':[ACTUAL_AUTHOR_ID],'artifact_ids':[]}]},'state':{YOUR_MEMORY}}. "
            'Only actual author IDs are legal. Empty messages remain legal. Do not fabricate papers, measurements or outcome claims. '
            'Messages can affect subsequent researcher prompts, not retrospectively create results. '
            'Think about whether previous conditions ever activated; activity is diagnostic, not an added reward. '
            'If prior source is inert on the supplied real paper/author records, consider revising its actual algorithm, '
            'not just its formatting or label. Explain what observation motivates the revision. '
            'No network, host files, third-party imports or utopia imports.\nDECLARED LOSS:\n' + json.dumps(loss_spec) +
            '\nPARENT INSTITUTION:\n' + json.dumps(node.to_dict() if hasattr(node, 'to_dict') else parent.to_dict()['mechanisms'][node_index]) +
            '\nACTUAL FEEDBACK:\n' + json.dumps(feedback, ensure_ascii=False) + '\nTASK:\n' + self.instructions)
        original_prompt = prompt
        binding = {'parent_fingerprint': parent.fingerprint, 'history_sha256': digest(history),
                   'loss_spec_sha256': digest(loss_spec), 'node_id': self.node_id, 'index': index,
                   'instructions_sha256': digest(self.instructions)}
        if self.planning:
            binding['planning'] = True
        schema = {'type': 'object', 'additionalProperties': False, 'required': ['rationale', 'label', 'source'],
                  'properties': {key: {'type': 'string'} for key in ('rationale', 'label', 'source')}}
        for attempt in range(self.max_attempts):
            path = self.receipts / f'source-revision-{index}-{attempt}.json'
            if path.exists():
                receipt = json.loads(path.read_text())
                if receipt['binding'] != binding or receipt['prompt_sha256'] != digest(prompt):
                    raise ValueError('source revision receipt binding changed')
                if receipt['status'] == 'isolated-probe-passed-not-native-evaluated':
                    candidate = apply_design_patch(parent, receipt['patch'])
                    if candidate.fingerprint != receipt['candidate_fingerprint']:
                        raise ValueError('source revision cached candidate changed')
                    return receipt['patch']
                draft, error = receipt['draft'], receipt['error']
            else:
                plan = None
                if self.planning:
                    plan_path = self.receipts / f'source-plan-{index}-{attempt}.json'
                    if plan_path.exists():
                        saved_plan = json.loads(plan_path.read_text())
                        if saved_plan['binding'] != binding or saved_plan['prompt_sha256'] != digest(prompt):
                            raise ValueError('source planning receipt changed')
                        plan = saved_plan['plan']
                    else:
                        plan_schema = {'type': 'object', 'additionalProperties': False,
                            'required': ['diagnosis', 'proposed_algorithm', 'evidence_used'],
                            'properties': {key: {'type': 'string'} for key in ('diagnosis', 'proposed_algorithm', 'evidence_used')}}
                        plan, _ = self.model.generate(prompt='Before writing code, diagnose why the prior algorithm did or did not act on these actual observations. Propose a substantive executable algorithm change targeting the declared loss. Return {diagnosis,proposed_algorithm,evidence_used}, not source code. Distinguish your hypothesis from an observed benefit.\n' + prompt,
                            system_prompt='You are a scientific-institution algorithm designer. Ground reasoning in supplied observations; do not merely justify unchanged code.',
                            seed_ctx=('native_source_plan', index, attempt), response_format={'type': 'json_schema', 'json_object': {'name': 'institution_plan', 'schema': plan_schema}})
                        if not isinstance(plan, dict) or set(plan) != {'diagnosis', 'proposed_algorithm', 'evidence_used'} or any(not isinstance(v, str) for v in plan.values()):
                            raise ValueError('invalid model planning output; no source or native score claimed')
                        write_json_atomic(plan_path, {'binding': binding, 'prompt_sha256': digest(prompt), 'plan': plan}, allow_nan=False)
                generation_prompt = prompt if plan is None else prompt + '\nYOUR RECORDED ALGORITHM PLAN (hypothesis, not proven improvement):\n' + json.dumps(plan) + '\nNow implement that plan in actual Python. A rationale-only change does not implement a changed algorithm. All technical contracts still apply.'
                draft, _ = self.model.generate(prompt=generation_prompt, seed_ctx=('native_source_revision', index, attempt),
                    system_prompt='You implement scientific-institution algorithms as executable Python. Write actual logic from the supplied evidence and task, not a cosmetic rewrite.',
                    max_tokens=4096, response_format={'type': 'json_schema', 'json_object': {'name': 'institution_revision', 'schema': schema}})
                receipt = {'binding': binding, 'prompt_sha256': digest(prompt), 'feedback': feedback, 'draft': draft, 'loss': None}
                if plan is not None:
                    receipt['plan_sha256'] = digest(plan)
                try:
                    if not isinstance(draft, dict) or set(draft) != {'label', 'source', 'rationale'}:
                        raise ValueError('exact source revision fields required')
                    artifact = {**clone(node.parameters['code_artifact']), 'source': draft['source'], 'label': draft['label']}
                    validate_code_artifact(artifact)
                    execution = self.executor.execute(artifact, {'period': world['year'], 'phase': 191,
                        'random_seed': latest['observation']['metadata']['runs'][0]['seed'], 'state': {},
                        'parameters': {k: clone(v) for k, v in node.parameters.items() if k not in {'code_artifact', 'runtime_image_id'}},
                        'inputs': {'observations': [{'payload': world, 'actor_ids': [], 'artifact_ids': []}]}})
                    authors = {a['id'] for a in world['ecosystem']['agents'] if a.get('can_author')}
                    messages = execution.result['outputs']['messages']
                    for message in messages:
                        if not message.get('actor_ids') or not set(message['actor_ids']) <= authors:
                            raise ValueError('output message must target existing author IDs')
                    patch = make_patch(parent, [{'op': 'replace', 'path': f'/mechanisms/{node_index}/parameters/code_artifact', 'value': artifact}], rationale=draft['rationale'])
                    candidate = apply_design_patch(parent, patch)
                    receipt.update(status='isolated-probe-passed-not-native-evaluated', patch=patch,
                        candidate_fingerprint=candidate.fingerprint, probe=execution.receipt,
                        probe_message_count=len(messages), source_sha256=digest(draft['source']))
                    write_json_atomic(path, receipt, allow_nan=False)
                    return patch
                except Exception as failure:
                    error = str(failure)[:3000]
                    receipt.update(status='invalid', error=error)
                    write_json_atomic(path, receipt, allow_nan=False)
            prompt = original_prompt + '\nYOUR LAST SOURCE:\n' + json.dumps(draft) + '\nACTUAL TECHNICAL ERROR:\n' + error
        raise ValueError('source revision exhausted technical repairs; no loss assigned')
