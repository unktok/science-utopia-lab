"""Restartable outer design loop over the actual native researcher world.

No new world equations, loss selection, implicit policy veto or host code eval.
One writer owns a campaign directory; model caches remain factory-owned.
"""
from __future__ import annotations

import json
from pathlib import Path

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, validate_loss_spec, loss_spec_sha256
from .native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import apply_design_patch, clone, design_difference, digest
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.native-design-campaign.v1'


class NativeDesignCampaign:
    """Persist proposal before execution and observation before next proposal.

    Resume repeats the same pending suggestion, never consumes a replacement
    suggestion. The factory must restore its native year/cache checkpoint. A
    completed response returned before a crash is reused there, not guessed here.
    """
    def __init__(self, directory, *, initial_system, loss_spec, seeds, world_binding):
        validate_loss_spec(loss_spec)
        if not seeds or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds):
            raise ValueError('distinct integer development seeds required')
        if not isinstance(world_binding, dict) or not world_binding:
            raise ValueError('explicit native world/model/corpus/fidelity binding required')
        self.directory = Path(directory)
        self.path = self.directory / 'native-design-state.json'
        self.initial = initial_system
        self.loss_spec = clone(loss_spec)
        self.seeds = list(seeds)
        self.binding = {'initial_system_fingerprint': initial_system.fingerprint,
                        'loss_spec_sha256': loss_spec_sha256(loss_spec),
                        'seeds': list(seeds), 'world': clone(world_binding)}
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            self._validate()
        else:
            self.state = {'schema': SCHEMA, 'binding': self.binding, 'records': [], 'pending': None}
            self._save()

    def _save(self):
        write_json_atomic(self.path, self.state, ensure_ascii=False, sort_keys=True, allow_nan=False)

    def _validate(self):
        if set(self.state) != {'schema', 'binding', 'records', 'pending'} or self.state['schema'] != SCHEMA or self.state['binding'] != self.binding:
            raise ValueError('native design campaign binding/schema changed')
        seen = set()
        for index, record in enumerate(self.state['records']):
            self._validate_record(record, index, seen, complete=True)
            seen.add(record['suggestion']['suggestion_id'])
        if self.state['pending'] is not None:
            self._validate_record(self.state['pending'], len(self.state['records']), seen, complete=False)

    def _validate_record(self, record, index, seen, *, complete):
        expected = {'suggestion', 'patch', 'difference', 'parent_system'} | ({'observation'} if complete else set())
        if set(record) != expected:
            raise ValueError('invalid native design record fields')
        suggestion = Suggestion.from_dict(record['suggestion'])
        if suggestion.proposal_index != index or suggestion.suggestion_id in seen:
            raise ValueError('native proposal sequence/identity changed')
        parent = SystemSpec.from_dict(record['parent_system'])
        if record['patch'] is None:
            if index != 0 or suggestion.candidate != self.initial.to_dict() or parent != self.initial:
                raise ValueError('only first suggestion may be the unedited initial system')
            expected_parent = None
        else:
            if apply_design_patch(parent, record['patch']).to_dict() != suggestion.candidate:
                raise ValueError('native patch and executed candidate differ')
            prior = [r for r in self.state['records'][:index]
                     if r['observation']['status'] == 'complete']
            best = min(prior, key=lambda r: r['observation']['loss']) if prior else None
            expected_parent = best['observation']['observation_id'] if best else None
            if parent.to_dict() != (best['suggestion']['candidate'] if best else self.initial.to_dict()):
                raise ValueError('native design parent is not the recorded incumbent')
        if suggestion.based_on_observation_id != expected_parent:
            raise ValueError('native proposal observation lineage changed')
        candidate = SystemSpec.from_dict(suggestion.candidate)
        identity = 'native-design-' + digest({'index': index, 'candidate': suggestion.candidate,
                                               'binding': self.binding})[:20]
        if suggestion.suggestion_id != identity or record['difference'] != design_difference(parent, candidate):
            raise ValueError('native suggestion identity/difference changed')
        if complete:
            observation = Observation.from_dict(record['observation'])
            if observation.suggestion_id != suggestion.suggestion_id or observation.candidate != suggestion.candidate:
                raise ValueError('native observation and suggestion differ')
            if observation.metadata.get('loss_spec_sha256') != self.binding['loss_spec_sha256']:
                raise ValueError('native observation loss binding changed')
            evaluated = evaluate_loss(self.loss_spec, observation.metadata.get('measurements', []))
            if (evaluated != observation.metadata.get('loss_evaluation')
                    or observation.loss != (evaluated['loss'] if evaluated['status'] == 'complete' else None)
                    or (observation.status == 'complete') != (evaluated['status'] == 'complete')):
                raise ValueError('native recorded loss does not match its measurements')
        return suggestion

    def incumbent(self):
        valid = [r for r in self.state['records'] if r['observation']['status'] == 'complete']
        return min(valid, key=lambda r: r['observation']['loss']) if valid else None

    def advance(self, *, simulation_factory, proposer=None):
        """Run one existing pending or newly proposed system. No automatic veto."""
        self._validate()
        record = self.state['pending']
        if record is None:
            index = len(self.state['records'])
            best = self.incumbent()
            parent = SystemSpec.from_dict(best['suggestion']['candidate']) if best else self.initial
            if index == 0:
                patch, candidate = None, self.initial
            else:
                if proposer is None:
                    raise ValueError('a result-conditioned native design proposer is required')
                patch = proposer(parent, clone(self.state['records']), index, clone(self.loss_spec))
                # Invalid proposals are recorded separately; they receive no score
                # and do not overwrite an already committed/pending proposal.
                try:
                    candidate = apply_design_patch(parent, patch)
                except Exception as error:
                    receipt = {'parent_fingerprint': parent.fingerprint, 'patch': patch,
                               'error_type': type(error).__name__, 'error': str(error)[:2000], 'loss': None}
                    rejection_id = digest(receipt)
                    write_json_atomic(self.directory / 'invalid-proposals' / (rejection_id + '.json'), receipt,
                                      sort_keys=True, allow_nan=False)
                    raise
            suggestion = Suggestion('native-design-' + digest({'index': index, 'candidate': candidate.to_dict(),
                'binding': self.binding})[:20], candidate.to_dict(), index,
                'initial' if index == 0 else 'adaptive', best['observation']['observation_id'] if best else None)
            record = {'suggestion': suggestion.to_dict(), 'patch': patch, 'parent_system': parent.to_dict(),
                      'difference': design_difference(parent, candidate)}
            self.state['pending'] = record
            self._save()
        suggestion = Suggestion.from_dict(record['suggestion'])
        observation = evaluate_native_suggestion(suggestion, seeds=self.seeds,
            simulation_factory=simulation_factory, loss_spec=self.loss_spec)
        completed = {**record, 'observation': observation.to_dict()}
        self.state['records'].append(completed)
        self.state['pending'] = None
        self._save()
        return clone(completed)


class LLMNativeDesignProposer:
    """An LLM edits protocols, source, nodes, wiring and schedules in one patch.

    Calls are recorded before repair. The caller supplies a model/cache and
    source-capability instructions; generated code is not executed by this class.
    """
    def __init__(self, model, *, instructions, receipts, max_attempts=3, named_edits=False, max_tokens=8192):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError('max_attempts must be in [1,5]')
        self.model, self.instructions, self.receipts, self.max_attempts = model, instructions, Path(receipts), max_attempts
        self.named_edits, self.max_tokens = named_edits, max_tokens

    def __call__(self, parent, history, index, loss_spec):
        prompt = ('Propose an executable science-system design patch, not a numeric substitute world. '
            'Return exactly {schema, parent_fingerprint, operations, rationale}. '
            'schema is scienceutopia.system-design-patch.v1. operations is a JSON-Patch-style list '
            'of {op:add|remove|replace,path:JSON-pointer,value:JSON}; remove omits value. '
            'You can add/remove/replace mechanisms, Python source or LLM instructions, ports, artifact types, '
            'connections, schedules and parameters. Joint producer/consumer changes are allowed. '
            'Return a changed system, not just a new label. Do not change the objective or claim measured improvement. '
            'Respect documented native phase prerequisites and sandbox capabilities.\n' + self.instructions +
            '\nPARENT:\n' + json.dumps(parent.to_dict(), ensure_ascii=False, sort_keys=True) +
            '\nDECLARED LOSS:\n' + json.dumps(loss_spec, sort_keys=True) +
            '\nPREVIOUS ACTUAL OBSERVATIONS:\n' + json.dumps(history, ensure_ascii=False, sort_keys=True))
        if self.named_edits:
            prompt = ('Design an executable new institution. Return exactly {schema,parent_fingerprint,changes,rationale}. '
                'schema=scienceutopia.system-design-intent.v1. changes is a list using stable IDs, not array indices. '
                'Allowed changes: {op:put_node,node:{mechanism_id,family,implementation,inputs:[{port_id,channel,artifact_type,required}],'
                'outputs:[...],parameters:{...}}}; {op:artifact_type,artifact_type:{artifact_type_id}}; '
                '{op:connect,connection:{source_mechanism,source_port,target_mechanism,target_port,channel,latency:0}}; '
                '{op:schedule,schedule:{mechanism_id,phase,trigger:annual}}; {op:remove_node,id}; '
                '{op:disconnect,connection:{...}}; '
                '{op:deliver_to_researchers,source:node_id,source_port:output_port,receiver:unique_id,phase:235,latency:0} '
                'installs the trusted typed delivery broker without any new institution algorithm; '
                '{op:edit,edit:{op:add|replace|remove,path,value}} for arbitrary other fields. '
                'Node defaults version=1, ports default required=true. Names cannot duplicate across a node inputs/outputs. '
                'New source algorithms, schemas and protocols are free; these are edit operations, not institution templates. '
                'Compile the final transaction atomically. Never import utopia/scienceutopia or third-party libraries in generated code.\n'
                + self.instructions + '\nPARENT:\n' + json.dumps(parent.to_dict(), sort_keys=True) +
                '\nDECLARED LOSS:\n' + json.dumps(loss_spec, sort_keys=True) +
                '\nACTUAL HISTORY (compact, no adopted trajectories):\n' + json.dumps([
                    {'suggestion_id': r['suggestion']['suggestion_id'], 'loss': r['observation']['loss'],
                     'status': r['observation']['status'], 'measurements': r['observation']['metadata']['measurements'],
                     'technical_failures': r['observation']['metadata']['technical_failures']} for r in history], sort_keys=True))
        original_prompt = prompt
        for attempt in range(self.max_attempts):
            patch, _ = self.model.generate(prompt=prompt, seed_ctx=('native_design_proposal', index, attempt), max_tokens=self.max_tokens)
            receipt = {'index': index, 'attempt': attempt, 'prompt_sha256': digest(prompt),
                       'parent_fingerprint': parent.fingerprint, 'history_sha256': digest(history),
                       'loss_spec_sha256': loss_spec_sha256(loss_spec), 'patch': patch}
            try:
                if self.named_edits:
                    from utopia.system.design_intent import compile_design_intent
                    patch = compile_design_intent(parent, patch)
                    receipt['compiled_patch'] = patch
                candidate = apply_design_patch(parent, patch)
                receipt.update(status='structurally_valid-not-runtime-validated', candidate_fingerprint=candidate.fingerprint)
            except Exception as error:
                receipt.update(status='invalid', error=str(error)[:3000], loss=None)
                write_json_atomic(self.receipts / f'proposal-{index}-{attempt}.json', receipt, allow_nan=False)
                prompt = original_prompt + '\nYOUR LAST PROPOSAL:\n' + json.dumps(receipt['patch'], sort_keys=True) + '\nACTUAL VALIDATION ERROR:\n' + str(error)[:3000]
                continue
            write_json_atomic(self.receipts / f'proposal-{index}-{attempt}.json', receipt, allow_nan=False)
            return patch
        raise ValueError('native design proposal exhausted technical repairs; no loss assigned')


def propose_from_native_world(parent, history, index, loss_spec):
    """Bridge an endogenous proposal to a separately evaluated next world.

    Chooses the last structurally valid matching proposal in the incumbent's
    first development run. This is explicit proposal selection, not a claim of
    observed improvement or recursive optimizer self-modification.
    """
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.utils.data_utils import file_sha256
    if not history:
        raise ValueError('no native observations from which to obtain a design proposal')
    valid = [r for r in history if r['observation']['status'] == 'complete']
    if not valid:
        raise ValueError('no complete native incumbent run')
    best = min(valid, key=lambda r: r['observation']['loss'])
    if best['suggestion']['candidate'] != parent.to_dict():
        raise ValueError('endogenous proposal parent and native incumbent differ')
    run = best['observation']['metadata']['runs'][0]
    path = Path(run['checkpoint_path'])
    if file_sha256(path) != run['checkpoint_sha256']:
        raise ValueError('endogenous proposal checkpoint hash changed')
    state = read_portable_checkpoint(path)['native_system']
    kernel = NativeScienceKernel(parent, checkpoint=state)
    proposals = [e.payload for e in kernel.events if e.event_type == 'native.system.design_proposed'
                 and e.payload['status'] == 'structurally_valid-not-evaluated'
                 and e.payload['patch']['parent_fingerprint'] == parent.fingerprint]
    if not proposals:
        raise ValueError('native world produced no structurally valid matching design proposal')
    return clone(proposals[-1]['patch'])
