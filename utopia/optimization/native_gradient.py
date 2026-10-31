"""Score-function design gradients measured in the native researcher world.

Estimates d E_z[L(native_system(sigmoid(z)))] / d mean for a Gaussian
proposal distribution. This does NOT backpropagate through native transitions,
LLM tokens or source synthesis. Bounds/coordinates are explicit caller design
choices; the world and LossSpec are never replaced with numeric world laws.
"""
from __future__ import annotations

import math

import torch

from .blackbox import Suggestion
from .loss import loss_spec_sha256, validate_loss_spec
from utopia.system.design_patch import apply_design_patch, clone, digest, make_patch, read_pointer

SCHEMA = 'scienceutopia.native-score-function.v1'


class NativeScoreFunctionSearch:
    def __init__(self, system, bindings, *, loss_spec, seed=0, sigma=0.7, learning_rate=0.1):
        validate_loss_spec(loss_spec)
        if (not bindings or type(seed) is not int or not math.isfinite(sigma) or sigma <= 0
                or not math.isfinite(learning_rate) or learning_rate <= 0):
            raise ValueError('explicit coordinates, seed, positive sigma/learning rate required')
        self.system, self.bindings, self.loss_hash = system, clone(bindings), loss_spec_sha256(loss_spec)
        self.seed, self.sigma, self.learning_rate = seed, float(sigma), float(learning_rate)
        means = []
        seen = set()
        for binding in self.bindings:
            if set(binding) != {'path', 'lower', 'upper'} or binding['path'] in seen:
                raise ValueError('invalid or duplicate gradient binding')
            seen.add(binding['path'])
            lower, upper = binding['lower'], binding['upper']
            value = read_pointer(system.to_dict(), binding['path'])
            if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in (lower, upper, value)) or not lower < value < upper):
                raise ValueError('gradient anchor must be strictly within finite declared bounds')
            fraction = (value - lower) / (upper - lower)
            means.append(math.log(fraction / (1 - fraction)))
        self.mean = torch.tensor(means, dtype=torch.float64, requires_grad=True)
        self.iteration = 0
        self.pending = []

    def ask(self, count=2):
        if self.pending or type(count) is not int or count < 2:
            raise ValueError('finish current batch first; at least two draws for leave-one-out baseline')
        generator = torch.Generator().manual_seed(int(digest({'seed': self.seed, 'iteration': self.iteration})[:15], 16))
        latent = self.mean.detach() + self.sigma * torch.randn((count, len(self.bindings)), generator=generator, dtype=torch.float64)
        for index, z in enumerate(latent):
            operations = [{'op': 'replace', 'path': binding['path'],
                           'value': binding['lower'] + (binding['upper'] - binding['lower']) * float(torch.sigmoid(value))}
                          for binding, value in zip(self.bindings, z)]
            patch = make_patch(self.system, operations, rationale='score-function native-world design sample')
            candidate = apply_design_patch(self.system, patch)
            identity = 'native-gradient-' + digest({'system': candidate.fingerprint, 'seed': self.seed,
                'iteration': self.iteration, 'draw': index, 'loss': self.loss_hash})[:20]
            suggestion = Suggestion(identity, candidate.to_dict(), self.iteration * count + index, 'score-function')
            self.pending.append({'suggestion': suggestion.to_dict(), 'patch': patch, 'latent': z.tolist()})
        return [Suggestion.from_dict(r['suggestion']) for r in self.pending]

    def tell(self, observations):
        if len(observations) != len(self.pending) or not self.pending:
            raise ValueError('one observation per pending native design draw required')
        by_id = {o.suggestion_id: o for o in observations}
        if len(by_id) != len(observations):
            raise ValueError('duplicate gradient observation')
        ordered = []
        for record in self.pending:
            suggestion = Suggestion.from_dict(record['suggestion'])
            observation = by_id.get(suggestion.suggestion_id)
            if (observation is None or observation.candidate != suggestion.candidate
                    or observation.metadata.get('loss_spec_sha256') != self.loss_hash
                    or observation.metadata.get('world_backend') != 'native-research-world'):
                raise ValueError('gradient observation candidate/loss/native-world binding mismatch')
            ordered.append(observation)
        report = {'schema': SCHEMA, 'iteration': self.iteration, 'method': 'native-loss-score-function',
                  'loss_spec_sha256': self.loss_hash, 'mean_before': self.mean.detach().tolist(),
                  'draws': clone(self.pending), 'observations': [o.to_dict() for o in ordered],
                  'end_to_end_native_autograd': False,
                  'gradient_target': 'expected native loss under declared bounded Gaussian-logistic design distribution'}
        # Dropping failed samples can bias the estimator; do not silently
        # optimize a conditional-on-success objective or invent failure losses.
        if any(o.status != 'complete' for o in ordered):
            report.update(status='not-updated-technical-failure', gradient=None)
        else:
            costs = torch.tensor([o.loss for o in ordered], dtype=torch.float64)
            baseline = (costs.sum() - costs) / (len(costs) - 1)
            latent = torch.tensor([r['latent'] for r in self.pending], dtype=torch.float64)
            log_probability = torch.distributions.Normal(self.mean, self.sigma).log_prob(latent).sum(-1)
            score_loss = ((costs - baseline).detach() * log_probability).mean()
            gradient, = torch.autograd.grad(score_loss, self.mean)
            updated = self.mean.detach() - self.learning_rate * gradient
            if not torch.isfinite(updated).all():
                raise ValueError('nonfinite score-function update')
            report.update(status='updated', losses=costs.tolist(), gradient=gradient.tolist(),
                          baseline='leave-one-out; independent of own design draw')
            self.mean = updated.requires_grad_()
        report['mean_after'] = self.mean.detach().tolist()
        self.iteration += 1
        self.pending = []
        return report

    def state_dict(self):
        return {'schema': SCHEMA, 'system': self.system.to_dict(), 'bindings': clone(self.bindings),
                'loss_spec_sha256': self.loss_hash, 'seed': self.seed, 'sigma': self.sigma,
                'learning_rate': self.learning_rate, 'iteration': self.iteration,
                'mean': self.mean.detach().tolist(), 'pending': clone(self.pending)}

    @classmethod
    def from_state(cls, state, *, loss_spec):
        from utopia.system import SystemSpec
        expected = {'schema', 'system', 'bindings', 'loss_spec_sha256', 'seed', 'sigma',
                    'learning_rate', 'iteration', 'mean', 'pending'}
        if set(state) != expected or state['schema'] != SCHEMA or state['loss_spec_sha256'] != loss_spec_sha256(loss_spec):
            raise ValueError('score-function checkpoint schema/loss mismatch')
        search = cls(SystemSpec.from_dict(state['system']), state['bindings'], loss_spec=loss_spec,
                     seed=state['seed'], sigma=state['sigma'], learning_rate=state['learning_rate'])
        if type(state['iteration']) is not int or state['iteration'] < 0:
            raise ValueError('invalid gradient iteration')
        mean = torch.tensor(state['mean'], dtype=torch.float64)
        if mean.shape != search.mean.shape or not torch.isfinite(mean).all():
            raise ValueError('invalid gradient mean')
        search.mean, search.iteration = mean.requires_grad_(), state['iteration']
        if state['pending']:
            search.ask(len(state['pending']))
            if search.pending != state['pending']:
                raise ValueError('gradient pending draws/patches changed')
        return search


class NativeGradientCampaign:
    """One-writer durable batches, including every observation before update."""
    def __init__(self, directory, search, *, loss_spec, seeds, world_binding):
        import json
        from pathlib import Path
        if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds) or not world_binding:
            raise ValueError('explicit native gradient seeds/world binding required')
        if search.pending or search.iteration:
            raise ValueError('campaign constructor needs the original search definition')
        self.path = Path(directory) / 'native-gradient-state.json'
        self.initial, self.loss_spec, self.seeds = search.state_dict(), clone(loss_spec), list(seeds)
        self.binding = {'search_definition': clone(self.initial), 'world': clone(world_binding), 'seeds': list(seeds)}
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            self._validate()
        else:
            self.state = {'schema': 'scienceutopia.native-gradient-campaign.v1', 'binding': self.binding,
                          'search': clone(self.initial), 'observations': [], 'reports': []}
            self._save()

    def _save(self):
        from utopia.utils.data_utils import write_json_atomic
        write_json_atomic(self.path, self.state, sort_keys=True, allow_nan=False)

    def _validate(self):
        from .blackbox import Observation
        from .loss import evaluate_loss
        if (set(self.state) != {'schema', 'binding', 'search', 'observations', 'reports'}
                or self.state['schema'] != 'scienceutopia.native-gradient-campaign.v1'
                or self.state['binding'] != self.binding):
            raise ValueError('native gradient campaign binding/schema changed')
        def checked(value):
            observation = Observation.from_dict(value)
            evaluated = evaluate_loss(self.loss_spec, observation.metadata.get('measurements', []))
            if (evaluated != observation.metadata.get('loss_evaluation')
                    or (observation.status == 'complete') != (evaluated['status'] == 'complete')
                    or observation.loss != (evaluated['loss'] if evaluated['status'] == 'complete' else None)):
                raise ValueError('native gradient loss/measurement evidence changed')
            return observation
        replayed = NativeScoreFunctionSearch.from_state(self.initial, loss_spec=self.loss_spec)
        for report in self.state['reports']:
            replayed.ask(len(report['draws']))
            if replayed.tell([checked(o) for o in report['observations']]) != report:
                raise ValueError('native gradient update history changed')
        saved = NativeScoreFunctionSearch.from_state(self.state['search'], loss_spec=self.loss_spec)
        if saved.pending:
            replayed.ask(len(saved.pending))
        if replayed.state_dict() != saved.state_dict() or len(self.state['observations']) > len(saved.pending):
            raise ValueError('native gradient pending search/history mismatch')
        for record, value in zip(saved.pending, self.state['observations']):
            observation = checked(value)
            if observation.suggestion_id != record['suggestion']['suggestion_id'] or observation.candidate != record['suggestion']['candidate']:
                raise ValueError('native gradient pending observation identity changed')
        return saved

    def advance(self, *, simulation_factory, count=2):
        from .blackbox import Observation
        from .native_world import evaluate_native_suggestion
        search = self._validate()
        if not search.pending:
            search.ask(count)
            self.state['search'] = search.state_dict()
            self._save()
        elif len(search.pending) != count:
            raise ValueError('resume must retain the pending native gradient batch size')
        for record in search.pending[len(self.state['observations']):]:
            observation = evaluate_native_suggestion(Suggestion.from_dict(record['suggestion']), seeds=self.seeds,
                simulation_factory=simulation_factory, loss_spec=self.loss_spec)
            self.state['observations'].append(observation.to_dict())
            self._save()
        report = search.tell([Observation.from_dict(o) for o in self.state['observations']])
        self.state['reports'].append(report)
        self.state['search'], self.state['observations'] = search.state_dict(), []
        self._save()
        return clone(report)
