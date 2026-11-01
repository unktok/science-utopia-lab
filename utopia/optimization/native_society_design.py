"""Objective-visible online institutional design in one persistent native society.

The portable society checkpoint is authoritative for adoption. A durable intent
precedes migration; receipt reconciliation repairs a crash before the journal
acknowledgement. This is not a causal policy comparison or designer improvement.
One local worker owns both the society and this journal. No code/LLM is invoked
by staging, measurement, confirmation, migration or recovery.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
from pathlib import Path

from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from .native_world import measure_native_boundary
from utopia.system import SystemSpec
from utopia.system.design_patch import apply_design_patch, clone, digest
from utopia.system.native_kernel import _hash
from utopia.system.native_migration import commit_native_design
from utopia.utils.data_utils import atomic_open, file_sha256, write_bytes_atomic

SCHEMA = "scienceutopia.native-society-design-session.v1"


class NativeSocietyDesignSession:
    """Observe -> author arbitrary patch -> explicit confirmation -> adopt -> observe.

    All mutation calls require a just-saved boundary in the synchronous native
    callback. Authorship can occur elsewhere, but a changed society invalidates
    its inspected checkpoint. A nonstationary online loss does not establish
    improvement against an unchanged counterfactual society.
    """

    def __init__(self, directory, *, founding_system, loss_spec, world_binding):
        validate_loss_spec(loss_spec)
        if (loss_spec['optimization_seed_role'] != 'development'
                or loss_spec['across_seeds']['minimum_valid_runs'] != 1):
            raise ValueError("online session requires an explicit one-society development loss")
        if not isinstance(world_binding, dict) or not world_binding:
            raise ValueError("explicit model/corpus/source world binding required")
        self.directory = Path(directory).resolve()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.directory / 'society-design.json'
        self.loss_spec = clone(loss_spec)
        self.founding = founding_system
        self.binding = {"founding_fingerprint": founding_system.fingerprint,
                        "loss_spec_sha256": loss_spec_sha256(loss_spec),
                        "world": clone(world_binding)}
        with self._lock():
            if not self.path.exists():
                self._save({"schema": SCHEMA, "binding": self.binding, "events": []})
            self._read()

    @contextmanager
    def _lock(self):
        path = self.directory / 'session.lock'
        if path.is_symlink():
            raise ValueError("session lock cannot be a symlink")
        with path.open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _read(self):
        if self.path.is_symlink():
            raise ValueError("session state cannot be a symlink")
        state = json.loads(self.path.read_text())
        if (set(state) != {'schema', 'binding', 'events'} or state['schema'] != SCHEMA
                or state['binding'] != self.binding or not isinstance(state['events'], list)):
            raise ValueError("society design session binding/schema changed")
        previous = None
        observations, requests, resolved = [], {}, set()
        for i, event in enumerate(state['events']):
            if (set(event) != {'index', 'kind', 'payload', 'previous_sha256', 'sha256'}
                    or event['index'] != i or event['previous_sha256'] != previous
                    or digest({k: v for k, v in event.items() if k != 'sha256'}) != event['sha256']):
                raise ValueError("society design journal hash chain changed")
            item = event['payload']
            if event['kind'] == 'bound':
                if i != 0 or item['founding_fingerprint'] != self.founding.fingerprint:
                    raise ValueError("actual society binding must be first and match its founding design")
            elif event['kind'] == 'observed':
                if (item['observation_id'] != 'society-observation-' + digest({k: v for k, v in item.items() if k != 'observation_id'})
                        or item['loss_spec_sha256'] != self.binding['loss_spec_sha256']
                        or evaluate_loss(self.loss_spec, [item['measurement']]) != item['loss_evaluation']
                        or item['loss'] != item['loss_evaluation']['loss']
                        or item['system_fingerprint'] != SystemSpec.from_dict(item['system']).fingerprint
                        or item['after_year'] != (observations[-1]['through_year'] if observations else 0)
                        or item['through_year'] <= item['after_year']):
                    raise ValueError("society observation measurements/identity differ")
                observations.append(item)
            elif event['kind'] == 'staged':
                body = {k: v for k, v in item.items() if k not in {'request_sha256', 'request_id'}}
                if (not observations or item['parent_observation_id'] != observations[-1]['observation_id']
                        or item['request_sha256'] != digest(body)
                        or item['request_id'] != 'society-design-' + item['request_sha256'][:24]
                        or item['request_sha256'] in requests
                        or set(requests) - resolved
                        or item['session_binding_sha256'] != digest(self.binding)
                        or item['loss_spec_sha256'] != self.binding['loss_spec_sha256']
                        or item['expected_checkpoint_sha256'] != observations[-1]['kernel_sha256']
                        or item['observed_society_sha256'] != observations[-1]['checkpoint_sha256']
                        or item['domain_sha256'] != observations[-1]['domain_sha256']):
                    raise ValueError("staged request identity/lineage differs")
                candidate = apply_design_patch(SystemSpec.from_dict(observations[-1]['system']), item['patch'])
                if candidate.to_dict() != item['candidate_system'] or candidate.fingerprint != item['candidate_fingerprint']:
                    raise ValueError("staged patch and candidate differ")
                requests[item['request_sha256']] = item
            elif event['kind'] in {'adopted', 'cancelled'}:
                request = requests.get(item['request_sha256'])
                if request is None or item['request_sha256'] in resolved or item['request_id'] != request['request_id']:
                    raise ValueError("resolved request lineage differs")
                if event['kind'] == 'adopted':
                    migration = item['migration']
                    if (digest({k: v for k, v in migration.items() if k != 'receipt_sha256'}) != migration['receipt_sha256']
                            or migration['receipt_sha256'] != item['migration_receipt_sha256']
                            or migration['target_spec'] != request['candidate_system']
                            or migration['parent_kernel_sha256'] != request['expected_checkpoint_sha256']
                            or migration['origin'].get('session_request_sha256') != item['request_sha256']):
                        raise ValueError("adoption and migration receipt differ")
                elif not isinstance(item.get('reason'), str) or not item['reason'].strip():
                    raise ValueError("cancellation reason required")
                resolved.add(item['request_sha256'])
            else:
                raise ValueError("unknown society design journal event")
            previous = event['sha256']
        return state

    def _save(self, state):
        with atomic_open(self.path, private=True, cleanup_on_error=True) as stream:
            json.dump(state, stream, sort_keys=True, ensure_ascii=False, allow_nan=False)
            stream.write('\n')

    def _append(self, state, kind, payload):
        event = {"index": len(state['events']), "kind": kind, "payload": clone(payload),
                 "previous_sha256": state['events'][-1]['sha256'] if state['events'] else None}
        event['sha256'] = digest(event)
        state['events'].append(event)
        self._save(state)
        return clone(payload)

    @staticmethod
    def _observations(state):
        return [e['payload'] for e in state['events'] if e['kind'] == 'observed']

    @staticmethod
    def _requests(state):
        return [e['payload'] for e in state['events'] if e['kind'] == 'staged']

    @staticmethod
    def _adoptions(state):
        return [e['payload'] for e in state['events'] if e['kind'] == 'adopted']

    @staticmethod
    def _resolved(state):
        return {e['payload']['request_sha256'] for e in state['events'] if e['kind'] in {'adopted', 'cancelled'}}

    def _boundary(self, simulation):
        """Check actual checkpoint/domain, not a browser's claimed measurement."""
        from utopia.runtime.checkpointing import capture_rng, read_portable_checkpoint
        kernel = simulation.native_system
        if kernel is None or kernel._frame is not None or kernel.last_year < 1:
            raise ValueError("completed native society boundary required")
        founding = (kernel.design_history[0]['source_spec'] if kernel.design_history
                    else kernel.spec.to_dict())
        if founding != self.founding.to_dict():
            raise ValueError("society founding design differs from session")
        path = Path(simulation.output_dir) / f'portable_checkpoint_year_{kernel.last_year}.json.gz'
        if (getattr(simulation, '_portable_active_checkpoint', None) != str(path.resolve())
                or getattr(simulation, '_portable_last_year', None) != kernel.last_year):
            raise ValueError("session mutation requires synchronous saved-boundary callback")
        saved = read_portable_checkpoint(path)
        if (saved.get('year') != kernel.last_year or saved.get('phase') != 5
                or saved.get('native_system') != kernel.to_dict()
                or saved['portable']['contract'] != simulation.portable_contract()
                or saved['portable']['rng'] != capture_rng()
                or saved['portable']['response_cache_count'] != simulation.llm.response_cache.committed_count()):
            raise ValueError("saved society, contract, RNG or response journal changed")
        actual_binding = self._actual_binding(simulation)
        state = self._read()
        if state['events'] and (state['events'][0]['kind'] != 'bound'
                or state['events'][0]['payload'] != actual_binding):
            raise ValueError("model/corpus/seed/config society binding differs from session")
        from utopia.runtime.checkpointing import pack_state
        current = simulation.capture_checkpoint_state(kernel.last_year, phase=5)
        if digest(pack_state(current)) != digest(pack_state(saved)):
            raise ValueError("unsaved complete native society state changed; adoption is stale")
        return path

    def _actual_binding(self, simulation):
        contract = clone(simulation.portable_contract())
        contract.pop('native_system', None)  # Only the institution design may migrate.
        return {'founding_fingerprint': self.founding.fingerprint,
                'portable_contract': contract,
                'response_cache_binding': clone(simulation.llm.response_cache.binding)}

    @staticmethod
    def _domain(simulation):
        conferences = simulation.conference_system.to_dict()
        for saved, current in zip(conferences['conferences'], simulation.conference_system.conferences):
            saved['submitted_papers'] = current.submitted_papers
        return {"ecosystem_data": simulation.ecosystem.to_dict(),
                "paper_tracker": simulation.paper_tracker.to_dict(),
                "funding_tracker": simulation.funding_tracker.to_dict(),
                "conference_system": conferences,
                "citation_tracker": simulation.citation_tracker.to_dict(),
                "submitted_paper_ids": sorted(simulation.submitted_paper_ids),
                "yearly_results": simulation.yearly_results}

    @classmethod
    def _domain_hash(cls, simulation):
        return digest(cls._domain(simulation))

    def _reconcile(self, state, simulation):
        history = simulation.native_system.design_history
        for adoption in self._adoptions(state):
            matches = [r for r in history if r['receipt_sha256'] == adoption['migration_receipt_sha256']]
            if len(matches) != 1 or matches[0] != adoption['migration']:
                raise ValueError("current society omits or rewrites an acknowledged adoption")
        # A previously inspected native event prefix must still be that prefix;
        # a rolled-back/forked society cannot inherit this session's feedback.
        from utopia.replay.events import canonical_event_stream_hash
        kernel = simulation.native_system
        for observation in self._observations(state):
            count = observation['native_event_count']
            if (kernel.last_year < observation['through_year'] or len(kernel.events) < count
                    or canonical_event_stream_hash(kernel.events[:count]) != observation['event_prefix_sha256']):
                raise ValueError("current society does not retain the observed native event prefix")
        adopted = self._resolved(state)
        for request in self._requests(state):
            if request['request_sha256'] in adopted:
                continue
            matches = [r for r in simulation.native_system.design_history
                       if r['origin'].get('session_request_sha256') == request['request_sha256']]
            if not matches:
                continue
            if len(matches) != 1:
                raise ValueError("request has multiple society migration receipts")
            receipt = matches[0]
            if (receipt['target_spec'] != request['candidate_system']
                    or receipt['parent_kernel_sha256'] != request['expected_checkpoint_sha256']
                    or receipt['origin'].get('loss_spec_sha256') != self.binding['loss_spec_sha256']):
                raise ValueError("society migration and staged request differ")
            self._append(state, 'adopted', {"request_sha256": request['request_sha256'],
                "request_id": request['request_id'], "after_year": receipt['after_year'],
                "candidate_fingerprint": request['candidate_fingerprint'],
                "migration_receipt_sha256": receipt['receipt_sha256'], "migration": receipt})

    def observe(self, simulation):
        with self._lock():
            state = self._read()
            path = self._boundary(simulation)
            if not state['events']:
                self._append(state, 'bound', self._actual_binding(simulation))
            self._reconcile(state, simulation)
            previous = self._observations(state)
            year = simulation.native_system.last_year
            if previous and previous[-1]['through_year'] == year:
                return clone(previous[-1])
            if previous and previous[-1]['through_year'] > year:
                raise ValueError("society is behind the design journal")
            after_year = previous[-1]['through_year'] if previous else 0
            measurement = measure_native_boundary(simulation,
                run_id=f'same-society-{year}', after_year=after_year)
            loss = evaluate_loss(self.loss_spec, [measurement])
            body = {"through_year": year, "after_year": after_year,
                    "system": simulation.native_system.spec.to_dict(),
                    "system_fingerprint": simulation.native_system.spec.fingerprint,
                    "kernel_sha256": _hash(simulation.native_system.to_dict()),
                    "native_event_count": len(simulation.native_system.events),
                    "event_prefix_sha256": simulation.native_system.to_dict()['event_stream_hash'],
                    "checkpoint_sha256": file_sha256(path), "domain_sha256": self._domain_hash(simulation),
                    "measurement": measurement, "loss_evaluation": loss,
                    "loss": loss['loss'], "loss_spec_sha256": self.binding['loss_spec_sha256'],
                    "preceding_adoption": self._adoptions(state)[-1]['request_sha256']
                        if self._adoptions(state) else None,
                    "comparison": "online-same-society-not-counterfactual"}
            body['observation_id'] = 'society-observation-' + digest(body)
            # Preserve the exact inspected whole society even when no edit follows.
            archive = self.directory / 'observed-societies' / (body['checkpoint_sha256'] + '.json.gz')
            if archive.is_symlink():
                raise ValueError("observed society archive cannot be a symlink")
            try:
                write_bytes_atomic(archive, path.read_bytes(), private=True, exclusive=True, readonly=True)
            except FileExistsError:
                if file_sha256(archive) != body['checkpoint_sha256']:
                    raise ValueError("observed society archive changed")
            return self._append(state, 'observed', body)

    def stage(self, *, parent_observation_id, patch, authoring,
              state_actions=None, discard_deliveries=None):
        """Record arbitrary exact source/graph edits; do not execute or score them."""
        with self._lock():
            state = self._read()
            observations = self._observations(state)
            if not observations or observations[-1]['observation_id'] != parent_observation_id:
                raise ValueError("proposal must use the latest observed society")
            observation = observations[-1]
            if any(a['after_year'] >= observation['through_year'] for a in self._adoptions(state)):
                raise ValueError("observe a later scientific interval before another adoption")
            adopted = self._resolved(state)
            if any(r['request_sha256'] not in adopted for r in self._requests(state)):
                raise ValueError("resolve the existing staged request before authoring a replacement")
            if not isinstance(authoring, dict) or not authoring.get('identity'):
                raise ValueError("explicit self-reported designer provenance required")
            parent = SystemSpec.from_dict(observation['system'])
            candidate = apply_design_patch(parent, patch)
            body = {"parent_observation_id": parent_observation_id,
                    "session_binding_sha256": digest(self.binding),
                    "expected_checkpoint_sha256": observation['kernel_sha256'],
                    "observed_society_sha256": observation['checkpoint_sha256'],
                    "domain_sha256": observation['domain_sha256'],
                    "candidate_fingerprint": candidate.fingerprint, "candidate_system": candidate.to_dict(),
                    "patch": clone(patch), "loss_spec_sha256": self.binding['loss_spec_sha256'],
                    "state_actions": clone(state_actions or {}),
                    "discard_deliveries": clone(discard_deliveries or {}), "authoring": clone(authoring)}
            body['request_sha256'] = digest(body)
            body['request_id'] = 'society-design-' + body['request_sha256'][:24]
            return self._append(state, 'staged', body)

    def adopt(self, simulation, *, request_id, confirmed_request_sha256):
        """Confirm exact inspected bytes; recover a previously committed migration."""
        with self._lock():
            state = self._read()
            self._boundary(simulation)
            self._reconcile(state, simulation)
            requests = [r for r in self._requests(state) if r['request_id'] == request_id]
            if len(requests) != 1 or requests[0]['request_sha256'] != confirmed_request_sha256:
                raise ValueError("explicit confirmation must match the exact staged request")
            request = requests[0]
            prior = [a for a in self._adoptions(state) if a['request_sha256'] == confirmed_request_sha256]
            if prior:
                return clone(prior[0])
            if confirmed_request_sha256 in self._resolved(state):
                raise ValueError("cancelled request cannot be adopted")
            kernel = simulation.native_system
            path = self._boundary(simulation)
            if (_hash(kernel.to_dict()) != request['expected_checkpoint_sha256']
                    or file_sha256(path) != request['observed_society_sha256']
                    or self._domain_hash(simulation) != request['domain_sha256']):
                raise ValueError("inspected society has changed; staged adoption is stale")
            commit_native_design(simulation, SystemSpec.from_dict(request['candidate_system']),
                expected_checkpoint_sha256=request['expected_checkpoint_sha256'],
                state_actions=request['state_actions'], discard_deliveries=request['discard_deliveries'],
                origin={"kind": "explicit-external-design", "session_request_sha256": confirmed_request_sha256,
                        "loss_spec_sha256": self.binding['loss_spec_sha256'],
                        "parent_observation_id": request['parent_observation_id']})
            self._reconcile(state, simulation)
            return clone(self._adoptions(state)[-1])

    def cancel(self, simulation, *, request_id, confirmed_request_sha256, reason):
        """Explicitly retire a failed/stale proposal, never erase its history."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("explicit cancellation reason required")
        with self._lock():
            state = self._read()
            self._boundary(simulation)
            self._reconcile(state, simulation)
            request = next((r for r in self._requests(state) if r['request_id'] == request_id), None)
            if request is None or request['request_sha256'] != confirmed_request_sha256:
                raise ValueError("cancellation confirmation must match the staged request")
            if confirmed_request_sha256 in self._resolved(state):
                raise ValueError("request is already resolved")
            return self._append(state, 'cancelled', {'request_id': request_id,
                'request_sha256': confirmed_request_sha256, 'reason': reason})

    def author(self, proposer, *, authoring, state_actions=None, discard_deliveries=None):
        """Call an external result-conditioned proposer; persist exact input binding.

        The proposer receives current graph, all interval observations/adoptions,
        proposal index and declared loss. It may author entirely new Python and
        protocols through the existing arbitrary patch API. It must not touch the
        society's RNG or inference journal while inside a saved-boundary callback.
        A missing/exhausted provider is not converted into a policy or a loss.
        """
        view = self.projection()
        if view['pending'] is not None:
            return view['pending']
        if not view['observations']:
            raise ValueError("observe actual scientific outcomes before authorship")
        parent = SystemSpec.from_dict(view['observations'][-1]['system'])
        index = len(view['requests'])
        feedback = {k: view[k] for k in ('observations', 'requests', 'adoptions', 'journal_sha256')}
        proposal_input = {'parent_system': parent.to_dict(), 'feedback': feedback,
                          'proposal_index': index, 'loss_spec': self.loss_spec}
        patch = proposer(parent, clone(feedback), index, clone(self.loss_spec))
        return self.stage(parent_observation_id=view['observations'][-1]['observation_id'],
            patch=patch, authoring={**clone(authoring), 'proposer_input_sha256': digest(proposal_input),
                                   'feedback_journal_sha256': view['journal_sha256']},
            state_actions=state_actions, discard_deliveries=discard_deliveries)

    def projection(self):
        """Data-only UI/proposer input; an available request is not an adoption."""
        with self._lock():
            state = self._read()
            adopted = self._resolved(state)
            pending = [r for r in self._requests(state) if r['request_sha256'] not in adopted]
            return {"schema": SCHEMA, "binding": clone(self.binding), "loss_spec": clone(self.loss_spec),
                    "actual_society_binding": clone(state['events'][0]['payload']) if state['events'] else None,
                    "observations": clone(self._observations(state)),
                    "requests": clone(self._requests(state)), "adoptions": clone(self._adoptions(state)),
                    "cancellations": [clone(e['payload']) for e in state['events'] if e['kind'] == 'cancelled'],
                    "pending": clone(pending[-1]) if pending else None,
                    "journal_sha256": state['events'][-1]['sha256'] if state['events'] else None,
                    "model_weights_trained": False, "causal_improvement_established": False}
