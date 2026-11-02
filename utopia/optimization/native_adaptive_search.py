"""Ongoing arbitrary design generation, mixed native search and designer feedback.

Generated source is data, executed only by the existing native factory's isolated
runtime. Score derivatives are likelihood derivatives, never source/LLM/world
pathwise derivatives. One writer owns each campaign directory.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import torch

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from .native_discrete_policy import verify_native_observation
from .native_factorized_gradient import NativeFactorizedDesignSearch
from .native_manifest_inbox import ExternalAuthoringPending
from .native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import apply_design_patch, clone, digest, make_patch, pointer, read_pointer
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.native-adaptive-open-search.v7'
VOCABULARY = 'scienceutopia.native-generated-vocabulary.v7'
EXPECTATION_ESTIMATOR = 'frozen-prior-control-variate-v11'


def expectation_compatibility(mixed):
    """Conservative semantic identity, not a guessed latent feature transport.

    Distribution means/logits and the base values overwritten by declared
    continuous draws may differ. All source, topology, factor choices, bounds,
    coordinate IDs/order and scales must otherwise be byte-identical JSON.
    """
    base = clone(mixed.base.to_dict())
    for coordinate in mixed.coordinates:
        owner = base
        parts = pointer(coordinate['path'])
        for part in parts[:-1]:
            owner = owner[int(part)] if isinstance(owner, list) else owner[part]
        key = int(parts[-1]) if isinstance(owner, list) else parts[-1]
        owner[key] = {'declared_continuous_coordinate': coordinate['id']}
    return digest({'base': base, 'factors': mixed.definition['factors'],
        'continuous': [{k: v for k, v in c.items() if k != 'mean'} for c in mixed.coordinates]})


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _apply_or_identity(parent, patch):
    if patch is None:
        # Validation-only identity transaction: validate arbitrary code/contracts
        # without importing/executing them or adding an authored semantic edit.
        patch = make_patch(parent, [{'op': 'replace', 'path': '/metadata', 'value': clone(parent.metadata)}])
    try:
        return apply_design_patch(parent, patch)
    except ValueError as error:
        if str(error) != 'design edit is a no-op':
            raise
        return parent  # Legal identity, never a repair/remap of an invalid edit.


class GeneratedMixedDesign:
    """A single immutable generated vocabulary, with fresh mixed IID draws.

    Definitions contain an arbitrary base patch, arbitrary conditional edit
    factors and independently sampled bounded continuous coordinates. There is
    no host institution/code catalogue. A later generator can replace/extend all
    of these, explicitly choosing whether to carry forward learned weights.
    """
    def __init__(self, parent, definition, *, loss_spec, seed, learning_rate=.1):
        required = {'base_patch', 'factors', 'continuous', 'provenance'}
        if (not isinstance(definition, dict) or not required <= set(definition)
                or set(definition) - required - {'logits'}
                or not isinstance(definition['provenance'], dict) or not definition['provenance']
                or not isinstance(definition['factors'], list) or not isinstance(definition['continuous'], list)
                or type(seed) is not int or not _finite(learning_rate) or learning_rate <= 0):
            raise ValueError('complete generated definition/provenance and finite search settings required')
        self.definition, self.loss = clone(definition), clone(loss_spec)
        self.parent, self.seed, self.learning_rate = parent, seed, float(learning_rate)
        self.base = _apply_or_identity(parent, definition['base_patch'])
        self.policy = (NativeFactorizedDesignSearch(self.base, definition['factors'], loss_spec=loss_spec,
            design_provenance=definition['provenance'], seed=seed, baseline='leave-one-out',
            learning_rate=learning_rate, logits=definition.get('logits')) if definition['factors'] else None)
        if self.policy is None and definition.get('logits') not in (None, {}):
            raise ValueError('no factor logits without declared factors')
        self.coordinates = clone(definition['continuous'])
        paths = []
        for coordinate in self.coordinates:
            if (not isinstance(coordinate, dict) or set(coordinate) != {'id', 'path', 'lower', 'upper', 'mean', 'sigma'}
                    or not isinstance(coordinate['id'], str) or not coordinate['id']
                    or coordinate['id'] in [c['id'] for c in self.coordinates[:len(paths)]]
                    or coordinate['path'] in paths
                    or any(not _finite(coordinate[k]) for k in ('lower', 'upper', 'mean', 'sigma'))
                    or coordinate['lower'] >= coordinate['upper'] or coordinate['sigma'] <= 0
                    or not math.isfinite(coordinate['upper'] - coordinate['lower'])):
                raise ValueError('unique explicit continuous IDs/paths and finite bounds/latent mean/sigma required')
            paths.append(coordinate['path'])
        # Every reachable structure must have the declared numeric coordinates.
        # No invalid structures are silently filtered to make sampling succeed.
        systems = [self.policy.compile_assignment(a)[0] for a in self.policy.assignments] if self.policy else [self.base]
        for system in systems:
            for coordinate in self.coordinates:
                if not _finite(read_pointer(system.to_dict(), coordinate['path'])):
                    raise ValueError('continuous path must already identify a finite numeric field in every structure')
        self.mean = torch.tensor([c['mean'] for c in self.coordinates], dtype=torch.float64, requires_grad=True)
        self.sigma = torch.tensor([c['sigma'] for c in self.coordinates], dtype=torch.float64)
        self.definition_sha256, self.base_sha256 = digest(self.definition), self.base.fingerprint
        self._sampled, self._sampling_weights, self._told = None, None, False

    def _check_definition(self):
        if (digest(self.definition) != self.definition_sha256 or self.base.fingerprint != self.base_sha256
                or self.coordinates != self.definition['continuous']
                or self.sigma.tolist() != [c['sigma'] for c in self.coordinates]
                or self.policy and digest(self.policy._definition()) != self.policy.space_sha256):
            raise ValueError('generated grammar/source/bounds/provenance changed after binding')

    def weights(self):
        return {'logits': {k: v.detach().tolist() for k, v in self.policy.logits.items()} if self.policy else {},
                'continuous_mean': self.mean.detach().tolist()}

    def log_probabilities(self, draws):
        discrete = (self.policy.action_log_probability([d['assignment'] for d in draws]) if self.policy else
                    torch.zeros(len(draws), dtype=torch.float64))
        if self.coordinates:
            latent = torch.tensor([d['latent'] for d in draws], dtype=torch.float64)
            discrete = discrete + torch.distributions.Normal(self.mean, self.sigma).log_prob(latent).sum(-1)
        return discrete

    def draw(self, count, *, version_sha256, proposal_start=0, based_on=None):
        self._check_definition()
        if self._sampled is not None:
            raise ValueError('one immutable batch per generated version instance')
        if type(count) is not int or count < 2:
            raise ValueError('at least two IID draws required for independent leave-one-out feedback')
        if self.policy:
            self.policy.ask(count)
            discrete = self.policy.pending
        else:
            discrete = [{'assignment': {}, 'suggestion': {'candidate': self.base.to_dict()}, 'factor_trace': []}
                        for _ in range(count)]
        rng_seed = int(digest({'seed': self.seed, 'purpose': 'continuous-native-design'})[:15], 16)
        rng = torch.Generator().manual_seed(rng_seed)
        latent = self.mean.detach() + self.sigma * torch.randn((count, len(self.coordinates)),
            generator=rng, dtype=torch.float64)
        if not torch.isfinite(latent).all():
            raise ValueError('nonfinite numerical latent draw; no replacement sample or numerical penalty')
        draws = []
        for index, (record, z) in enumerate(zip(discrete, latent)):
            system = SystemSpec.from_dict(record['suggestion']['candidate'])
            operations = [{'op': 'replace', 'path': c['path'],
                'value': c['lower'] + (c['upper'] - c['lower']) * float(torch.sigmoid(value))}
                for c, value in zip(self.coordinates, z)]
            patch = make_patch(system, operations, rationale='explicit bounded latent continuous design draw') if operations else None
            draw = {'assignment': record['assignment'], 'factor_trace': record['factor_trace'],
                'latent': z.tolist(), 'continuous_operations': operations, 'rng_seed': rng_seed,
                'suggestion': None, 'technical_error': None}
            try:
                candidate = _apply_or_identity(system, patch)
                identity = 'native-adaptive-' + digest({'version': version_sha256, 'index': index,
                    'assignment': draw['assignment'], 'latent': draw['latent'], 'candidate': candidate.fingerprint})[:24]
                draw['suggestion'] = Suggestion(identity, candidate.to_dict(), proposal_start + index,
                    'generated-mixed-native', based_on).to_dict()
            except Exception as error:
                draw['technical_error'] = {'type': type(error).__name__, 'message': str(error)[:2000], 'loss': None}
            draws.append(draw)
        for draw, logq in zip(draws, self.log_probabilities(draws).detach().tolist()):
            draw['conditional_latent_log_probability'] = logq
        self._sampled, self._sampling_weights = clone(draws), self.weights()
        return draws

    def update(self, draws, observations, *, score, estimator_context=None):
        self._check_definition()
        if (self._told or self._sampled != draws or self.weights() != self._sampling_weights
                or len(observations) != len(draws) or len(draws) < 2):
            raise ValueError('stale/changed mixed grammar, weights, draw choices or tell batch')
        before = self.weights()
        costs = [o['loss'] if o is not None else None for o in observations]
        valid = all(o is not None and o['status'] == 'complete' and not o['metadata'].get('technical_failures')
                    for o in observations)
        report = {'weights_before': before, 'weights_after': before, 'losses': costs,
            'gradient': None, 'status': 'not-updated-technical-failure' if not valid else 'blackbox-observed',
            'pathwise_native_or_llm_or_source_derivative': False,
            'likelihood_scope': 'exact declared conditional discrete assignment + Gaussian latent; fixed logistic pushforward',
            'sampling_note': 'IID conditional on one selected designer strategy; failed samples never dropped or numerically penalized'}
        if valid:
            report.update(all_equal_costs=len(set(costs)) == 1, all_zero_costs=all(c == 0 for c in costs))
        if valid and score and (self.policy or self.coordinates):
            parameters = [*self.policy.logits.values()] if self.policy else []
            if self.coordinates:
                parameters.append(self.mean)
            if estimator_context is None:
                costs_tensor = torch.tensor(costs, dtype=torch.float64)
                baseline = (costs_tensor.sum() - costs_tensor) / (len(costs) - 1)
                loss = ((costs_tensor - baseline).detach() * self.log_probabilities(draws)).mean()
                gradients = torch.autograd.grad(loss, parameters)
                gradient = {'logits': {key: value.detach().tolist() for key, value in
                    zip([*self.policy.logits] if self.policy else [], gradients)}}
                if self.coordinates:
                    gradient['continuous_mean'] = gradients[-1].tolist()
                baseline_note = 'leave-one-out excludes own IID conditional draw; equal costs give exactly zero advantages'
            else:
                from .native_expectation_estimators import estimate_expected_loss_gradient
                estimate = estimate_expected_loss_gradient(draws, costs,
                    logits=self.policy.logits if self.policy else {}, mean=self.mean, sigma=self.sigma,
                    discrete_log_probability=self.policy.action_log_probability if self.policy else None,
                    assignments=self.policy.assignments if self.policy else [{}],
                    control_variate=estimator_context['control_variate'],
                    sample_ids=estimator_context['sample_ids'], batch_id=estimator_context['batch_id'])
                report['expectation_estimator'] = {**estimate,
                    'prior_fit': estimator_context['prior_fit'],
                    'compatibility_sha256': expectation_compatibility(self)}
                if estimate['status'] != 'valid':
                    # Retain the exact failed estimator receipt and native losses;
                    # neither inner nor outer policy may update from this batch.
                    report['status'] = 'not-updated-estimator-failure'
                    self._told = True
                    return report
                gradient = estimate['gradient']
                gradients = [torch.tensor(gradient['logits'][key], dtype=torch.float64)
                    for key in (self.policy.logits if self.policy else {})]
                if self.coordinates:
                    gradients.append(torch.tensor(gradient['continuous_mean'], dtype=torch.float64))
                baseline_note = 'prior-only frozen surrogate residual score plus exact surrogate expectation derivative; no current-batch fitting'
            for parameter, g in zip(parameters, gradients):
                updated = parameter.detach() - self.learning_rate * g
                if not torch.isfinite(updated).all():
                    raise ValueError('nonfinite mixed policy update')
                with torch.no_grad():
                    parameter.copy_(updated)
            report.update(status='score-updated', gradient=gradient, weights_after=self.weights(),
                baseline=baseline_note)
        self._told = True
        return report


class NativeAdaptiveDesignCampaign:
    """Durable generation -> native draws -> actual-loss strategy feedback.

    A strategy is an arbitrary *caller-provided trusted generator*, not generated
    Python executed on the host. Its immutable provenance is caller-declared,
    not authenticated authorship. Every advance calls the selected generator
    again after the preceding completed feedback; no frozen design bank ceiling.
    """
    def __init__(self, directory, *, initial_system, loss_spec, seeds, world_binding,
                 strategies, mode='hybrid', seed=42, learning_rate=.1,
                 strategy_learning_rate=.1, strategy_baseline=0., exploration=.1,
                 expectation_estimator=None):
        validate_loss_spec(loss_spec)
        if (mode not in {'blackbox', 'score', 'hybrid'} or type(seed) is not int
                or not seeds or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds)
                or not isinstance(world_binding, dict) or not world_binding
                or any(not world_binding.get(k) for k in ('source_commit', 'model_digest', 'corpus_sha256'))
                or not isinstance(strategies, dict) or not strategies
                or any(not isinstance(k, str) or not k or not isinstance(v, dict) or not v for k, v in strategies.items())
                or not _finite(learning_rate) or learning_rate <= 0
                or not _finite(strategy_learning_rate) or strategy_learning_rate <= 0
                or not _finite(strategy_baseline) or not _finite(exploration) or not 0 < exploration <= 1):
            raise ValueError('explicit strategy provenance, source/model/corpus/seeds and finite optimizer settings required')
        self.directory, self.initial, self.loss = Path(directory), initial_system, clone(loss_spec)
        self.path = self.directory / 'native-adaptive-state.json'
        self.binding = {'initial_system': initial_system.to_dict(), 'loss_spec': clone(loss_spec),
            'world': clone(world_binding), 'seeds': list(seeds), 'strategies': clone(strategies),
            'mode': mode, 'seed': seed, 'learning_rate': float(learning_rate),
            'strategy_learning_rate': float(strategy_learning_rate), 'strategy_baseline': float(strategy_baseline),
            'exploration': float(exploration)}
        if expectation_estimator is not None:
            if (not isinstance(expectation_estimator, dict)
                    or set(expectation_estimator) != {'name', 'ridge'}
                    or expectation_estimator['name'] != EXPECTATION_ESTIMATOR
                    or not _finite(expectation_estimator['ridge']) or expectation_estimator['ridge'] <= 0
                    or mode == 'blackbox'):
                raise ValueError('explicit supported expectation estimator/ridge and score mode required')
            self.binding['expectation_estimator'] = clone(expectation_estimator)
        self.binding_sha256 = digest(self.binding)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            self._validate()
        else:
            self.state = {'schema': SCHEMA, 'binding': clone(self.binding), 'records': [], 'pending': None}
            self._save()

    def _save(self):
        write_json_atomic(self.path, self.state, sort_keys=True, allow_nan=False)

    def _strategy_initial(self):
        return {'logits': [0.] * len(self.binding['strategies']),
            'statistics': {key: {'batches': 0, 'loss_sum': 0.} for key in sorted(self.binding['strategies'])}}

    @staticmethod
    def _history(records):
        return [{key: clone(record[key]) for key in ('request_sha256', 'version_sha256', 'definition',
            'generation_error', 'draws', 'observations', 'report')} for record in records]

    def _request(self, records, strategy_state, count):
        ids = sorted(self.binding['strategies'])
        logits = torch.tensor(strategy_state['logits'], dtype=torch.float64)
        probabilities = (1 - self.binding['exploration']) * logits.softmax(0) + self.binding['exploration'] / len(ids)
        index = len(records)
        rng_seed = int(digest({'seed': self.binding['seed'], 'generation': index})[:15], 16)
        chosen = int(torch.multinomial(probabilities, 1, generator=torch.Generator().manual_seed(rng_seed)))
        observations = [{'suggestion': d['suggestion'], 'observation': o} for r in records
            for d, o in zip(r['draws'], r['observations']) if d['suggestion'] is not None and o is not None]
        valid = [r for r in observations if r['observation']['status'] == 'complete'
                 and not r['observation']['metadata'].get('technical_failures')]
        incumbent = min(valid, key=lambda r: r['observation']['loss']) if valid else None
        return {'schema': VOCABULARY, 'generation': index, 'count': count,
            'parent_system': incumbent['suggestion']['candidate'] if incumbent else self.initial.to_dict(),
            'based_on_observation_id': incumbent['observation']['observation_id'] if incumbent else None,
            'history': self._history(records), 'observations': observations, 'loss_spec': self.loss,
            'world_binding': self.binding['world'], 'strategy_id': ids[chosen],
            'strategy_provenance': self.binding['strategies'][ids[chosen]],
            'strategy_state': clone(strategy_state), 'strategy_probabilities': probabilities.tolist(),
            'strategy_log_probability': float(probabilities[chosen].log()), 'rng_seed': rng_seed,
            'binding_sha256': digest(self.binding), 'history_sha256': digest(records)}

    def _mixed(self, record):
        return GeneratedMixedDesign(SystemSpec.from_dict(record['request']['parent_system']), record['definition'],
            loss_spec=self.loss, seed=record['request']['rng_seed'], learning_rate=self.binding['learning_rate'])

    def _compile(self, record):
        mixed = self._mixed(record)
        draws = mixed.draw(record['request']['count'], version_sha256=record['version_sha256'],
            proposal_start=sum(len(r['draws']) for r in record['request']['history']),
            based_on=record['request']['based_on_observation_id'])
        return mixed, draws

    def _finish(self, record, strategy_state):
        state = clone(strategy_state)
        if record['generation_error']:
            return {'status': 'invalid-generated-vocabulary', 'loss': None, 'strategy_before': state,
                    'strategy_after': state, 'mixed': None, 'strategy_gradient': None}
        mixed, _ = self._compile(record)
        context = self._expectation_context(record, mixed) if 'expectation_estimator' in self.binding else None
        report = mixed.update(record['draws'], record['observations'], score=self.binding['mode'] != 'blackbox',
            estimator_context=context)
        before = clone(state)
        outer_gradient = None
        if report['status'] not in {'not-updated-technical-failure', 'not-updated-estimator-failure'}:
            cost = math.fsum(report['losses']) / len(report['losses'])
            key = record['request']['strategy_id']
            stats = state['statistics'][key]
            stats['batches'] += 1
            stats['loss_sum'] += cost
            if self.binding['mode'] != 'blackbox':
                logits = torch.tensor(state['logits'], dtype=torch.float64, requires_grad=True)
                rho, size = self.binding['exploration'], len(logits)
                p = (1-rho) * logits.softmax(0) + rho / size
                selected = sorted(self.binding['strategies']).index(key)
                # ONE strategy draw per batch: its score is NOT multiplied by count.
                objective = (cost - self.binding['strategy_baseline']) * p[selected].log()
                gradient, = torch.autograd.grad(objective, logits)
                outer_gradient = gradient.tolist()
                state['logits'] = (logits.detach() - self.binding['strategy_learning_rate'] * gradient).tolist()
            if self.binding['mode'] in {'blackbox', 'hybrid'}:
                # Explicit black-box strategy selection heuristic; no unbiased-gradient claim.
                for i, identity in enumerate(sorted(self.binding['strategies'])):
                    s = state['statistics'][identity]
                    if s['batches']:
                        target = -s['loss_sum'] / s['batches']
                        rate = self.binding['strategy_learning_rate']
                        state['logits'][i] = (1-rate)*state['logits'][i] + rate*target
            if any(not math.isfinite(v) for v in state['logits']):
                raise ValueError('nonfinite designer strategy update')
        return {'status': report['status'], 'mixed': report, 'strategy_before': before, 'strategy_after': state,
            'strategy_gradient': outer_gradient,
            'batch_joint_latent_log_probability': record['request']['strategy_log_probability'] +
                math.fsum(d['conditional_latent_log_probability'] for d in record['draws']),
            'strategy_scope': 'external generator selection and its future feedback, not source-content backpropagation',
            'score_scope': 'conditional current-vocabulary likelihood score; unknown generator-source probabilities and direct generator dependence on exposed weights/history are not differentiated',
            'sampling_note': 'one shared strategy draw; conditional IID design draws; outer score uses independent fixed baseline; nonzero equal-cost score noise is not comparative evidence',
            'hybrid_is_heuristic': self.binding['mode'] == 'hybrid'}

    def _expectation_context(self, record, mixed):
        """Fit only compatible, preceding, valid native data from this arm.

        A changed source, factor grammar or coordinate meaning resets the model;
        no invented feature transport and no other-arm/future observations.
        """
        from .native_expectation_estimators import FrozenDesignControlVariate
        compatibility = expectation_compatibility(mixed)
        draws, losses, ids, batches, incompatible = [], [], [], [], []
        for prior in record['request']['history']:
            if prior['generation_error']:
                continue
            # History records already carry their fit compatibility receipt. A
            # first-batch receipt exists even when no earlier model was fitted.
            prior_estimator = (prior['report'].get('mixed') or {}).get('expectation_estimator')
            if prior_estimator is None or prior_estimator['compatibility_sha256'] != compatibility:
                incompatible.append(prior['request_sha256'])
                continue
            for draw, observation in zip(prior['draws'], prior['observations']):
                if observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures'):
                    draws.append(draw)
                    losses.append(observation['loss'])
                    ids.append(observation['observation_id'])
                    batches.append(prior['request_sha256'])
        assignments = mixed.policy.assignments if mixed.policy else [{}]
        model = (FrozenDesignControlVariate.fit(draws, losses, sample_ids=ids, batch_ids=batches,
            assignments=assignments, latent_dim=len(mixed.coordinates),
            ridge=self.binding['expectation_estimator']['ridge']) if draws else None)
        return {'control_variate': model, 'sample_ids': [o['observation_id'] if o else
            'invalid-' + str(i) for i, o in enumerate(record['observations'])],
            'batch_id': record['request_sha256'],
            'prior_fit': {'status': 'fitted-prior-only' if model is not None else 'no-compatible-prior-plain-lr',
                'sample_ids': ids, 'batch_ids': batches, 'incompatible_prior_batches': incompatible,
                'frozen_model': model.to_dict() if model is not None else None}}

    def _check_observation(self, value, draw):
        if draw['suggestion'] is None:
            if value is not None:
                raise ValueError('invalid design cannot receive native numerical evidence')
            return
        observation = Observation.from_dict(value)
        suggestion = draw['suggestion']
        evaluated = evaluate_loss(self.loss, observation.metadata.get('measurements', []))
        if (observation.suggestion_id != suggestion['suggestion_id'] or observation.candidate != suggestion['candidate']
                or observation.metadata.get('world_backend') != 'native-research-world'
                or observation.metadata.get('loss_spec_sha256') != loss_spec_sha256(self.loss)
                or observation.metadata.get('loss_evaluation') != evaluated
                or observation.loss != (evaluated['loss'] if evaluated['status'] == 'complete' else None)
                or (observation.status == 'complete') != (evaluated['status'] == 'complete')):
            raise ValueError('native observation/measurement/loss/design changed')
        verify_native_observation(observation, self.binding['world'], self.binding['seeds'])

    def _validate(self):
        if (set(self.state) != {'schema', 'binding', 'records', 'pending'} or self.state['schema'] != SCHEMA
                or self.state['binding'] != self.binding or digest(self.binding) != self.binding_sha256
                or self.loss != self.binding['loss_spec'] or self.initial.to_dict() != self.binding['initial_system']):
            raise ValueError('adaptive campaign binding changed')
        strategy = self._strategy_initial()
        records = []
        for complete, record in [(True, r) for r in self.state['records']] + (
                [(False, self.state['pending'])] if self.state['pending'] is not None else []):
            expected_keys = {'request', 'request_sha256', 'definition', 'version_sha256', 'generation_error',
                             'draws', 'observations', 'report', 'generated', 'compiled'}
            if set(record) != expected_keys:
                raise ValueError('adaptive generation record fields changed')
            request = self._request(records, strategy, record['request']['count'])
            if request != record['request'] or digest(request) != record['request_sha256']:
                raise ValueError('designer strategy/history/weights/request changed')
            definition = record['definition']
            if type(record['generated']) is not bool or type(record['compiled']) is not bool:
                raise ValueError('invalid durable generation stage')
            if not record['generated']:
                if (definition is not None or record['version_sha256'] is not None or record['draws']
                        or record['observations'] or record['generation_error'] or record['compiled'] or complete):
                    raise ValueError('unbound vocabulary cannot have draws or costs')
            else:
                if record['version_sha256'] != digest({'request': record['request_sha256'], 'definition': definition}):
                    raise ValueError('immutable generated grammar/source/provenance changed')
                if not record['compiled']:
                    if record['draws'] or record['observations'] or record['generation_error'] or complete:
                        raise ValueError('uncompiled vocabulary cannot have execution evidence')
                elif not record['generation_error']:
                    _, expected = self._compile(record)
                    if expected != record['draws']:
                        raise ValueError('mixed draws/grammar/weights/likelihood changed')
                else:
                    try:
                        self._compile(record)
                    except Exception as error:
                        if record['generation_error'] != {'type': type(error).__name__, 'message': str(error)[:2000], 'loss': None}:
                            raise ValueError('generation technical error changed') from error
                    else:
                        raise ValueError('valid vocabulary relabelled invalid')
            if len(record['observations']) > len(record['draws']):
                raise ValueError('too many observations for generated batch')
            for draw, value in zip(record['draws'], record['observations']):
                self._check_observation(value, draw)
            if complete:
                if not record['generation_error'] and (definition is None or len(record['observations']) != len(record['draws'])):
                    raise ValueError('completed generation needs all observations')
                report = self._finish(record, strategy)
                if report != record['report']:
                    raise ValueError('native strategy or mixed update history changed')
                strategy = clone(report['strategy_after'])
                records.append(record)
            elif record['report'] is not None:
                raise ValueError('pending generation already has an update')
        return strategy

    def advance(self, *, simulation_factory, generators, count=2):
        """Generate once per saved request; execute/resume draws, then commit tell.

        Generators take the complete exact request dictionary. External inbox
        waits preserve it. Invalid vocabularies/draws get null costs and are not
        repaired/resampled; a later explicit advance generates a new version.
        """
        if type(count) is not int or count < 2:
            raise ValueError('at least two draws required')
        strategy = self._validate()
        record = self.state['pending']
        if record is None:
            request = self._request(self.state['records'], strategy, count)
            record = {'request': request, 'request_sha256': digest(request), 'definition': None,
                      'version_sha256': None, 'generation_error': None, 'draws': [], 'observations': [], 'report': None,
                      'generated': False, 'compiled': False}
            self.state['pending'] = record
            self._save()
        elif record['request']['count'] != count:
            raise ValueError('resume must keep the pending batch size')
        if not record['generated']:
            identity = record['request']['strategy_id']
            if identity not in generators or not callable(generators[identity]):
                raise ValueError('selected trusted external generator is missing')
            try:
                definition = generators[identity](clone(record['request']))
            except ExternalAuthoringPending:
                raise
            # Persist exact JSON before compile, native execution or future generation.
            # Callback exceptions propagate (not silently scored/retried); saved request survives.
            record['definition'] = clone(definition)
            record['version_sha256'] = digest({'request': record['request_sha256'], 'definition': definition})
            record['generated'] = True
            self._save()
        if not record['compiled']:
            try:
                _, record['draws'] = self._compile(record)
            except Exception as error:
                record['generation_error'] = {'type': type(error).__name__, 'message': str(error)[:2000], 'loss': None}
            record['compiled'] = True
            self._save()
        for draw in record['draws'][len(record['observations']):]:
            observation = (evaluate_native_suggestion(Suggestion.from_dict(draw['suggestion']),
                seeds=self.binding['seeds'], simulation_factory=simulation_factory, loss_spec=self.loss).to_dict()
                if draw['suggestion'] is not None else None)
            if draw['suggestion'] is not None:
                self._check_observation(observation, draw)
            record['observations'].append(observation)
            self._save()
        record['report'] = self._finish(record, strategy)
        self.state['records'].append(record)
        self.state['pending'] = None
        self._save()
        return clone(record)


class PatchProposerGenerator:
    """Adapt an existing native patch proposer into continued generation.

    Optional definition_builder(request, patch) may additionally author free
    factors, evolving choices and continuous coordinates. No body/wire repair.
    """
    def __init__(self, proposer, *, provenance, definition_builder=None):
        self.proposer, self.provenance, self.builder = proposer, clone(provenance), definition_builder

    def __call__(self, request):
        patch = self.proposer(SystemSpec.from_dict(request['parent_system']), clone(request['observations']),
            request['generation'] + 1, clone(request['loss_spec']))
        if self.builder:
            return self.builder(clone(request), patch)
        return {'base_patch': patch, 'factors': [], 'continuous': [], 'provenance': self.provenance}


class InboxVocabularyGenerator:
    """Hash-bound ManifestInbox authoring, with zero hidden source generation."""
    def __init__(self, inbox, *, instructions):
        self.inbox, self.instructions = inbox, instructions

    def __call__(self, request):
        definition, _ = self.inbox.generate(system='External open native design generation; fixed researcher weights.',
            prompt='Return a complete JSON definition {base_patch,factors,continuous,provenance, optional logits}. '
                'base_patch is a full scienceutopia.system-design-patch.v1 or null. factors are arbitrary '
                'NativeFactorizedDesignSearch edit choices with explicit provenance and optional earlier-choice support. '
                'continuous entries are {id,path,lower,upper,mean,sigma}: Gaussian latent followed by logistic bounds. '
                'Return [] when no factors/coordinates are needed. All semantic source/protocol/wires must be authored '
                'explicitly. Inspect actual losses and previous updated weights; you may invent new options/code '
                'or explicitly carry their learned weights into this new version. No hidden merit veto.\n' + self.instructions,
            authoring_input=clone(request), seed_ctx=['native-adaptive-generation-v7', request['request_sha256']]
                if 'request_sha256' in request else ['native-adaptive-generation-v7', digest(request)],
            output_schema={'type': 'object'}, settings={'source_execution_on_host': False})
        return definition
