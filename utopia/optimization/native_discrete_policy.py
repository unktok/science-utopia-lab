"""REINFORCE over arbitrary complete scientific SystemSpecs, not Gaussian ES.

Candidate source/graphs may be generated elsewhere; this optimizer does not
claim to invent them. A categorical (or two-way Bernoulli) design policy is
learned from complete native-world loss with all downstream fixed-LLM replies.
Autograd differentiates exact log probabilities, NOT native executions.
"""
from __future__ import annotations

import math
import torch

from .blackbox import Suggestion
from .loss import loss_spec_sha256, validate_loss_spec
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-discrete-policy.v1'


def verify_native_observation(observation, world, seeds):
    """Bind durable successful draws to exact world, RNG seed and checkpoint.

    A failed draw remains a failure, never an invented numerical cost. This
    verifies receipt identity; independent report audit still derives domain
    measurements from checkpoints rather than trusting the optimizer.
    """
    from pathlib import Path
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.utils.data_utils import file_sha256
    runs = observation.metadata.get('runs', [])
    if observation.status != 'complete' or observation.metadata.get('technical_failures'):
        return
    if len(runs) != len(seeds) or {r['seed'] for r in runs} != set(seeds):
        raise ValueError('discrete policy requires all declared native replicate receipts')
    design = SystemSpec.from_dict(observation.candidate)
    for run in runs:
        checkpoint = Path(run.get('checkpoint_path', ''))
        if not checkpoint.is_file() or file_sha256(checkpoint) != run.get('checkpoint_sha256'):
            raise ValueError('discrete policy native checkpoint missing or changed')
        state = read_portable_checkpoint(checkpoint)
        binding = state['portable']['contract']['binding']
        if (binding['cell'] != design.fingerprint or binding['seed'] != run['seed']
                or binding['model_revision'] != world['model_digest']
                or binding['corpus_sha256'] != world['corpus_sha256']
                or binding['science_config']['source_commit'] != world['source_commit']):
            raise ValueError('discrete policy native source/model/corpus/design/RNG binding differs')
        kernel = NativeScienceKernel(design, checkpoint=state['native_system'])
        horizon = state['portable']['contract']['simulation']['num_years']
        if (type(horizon) is not int or horizon < 1 or state.get('phase') != 5
                or state.get('year') != horizon or kernel.last_year != horizon
                or run.get('system_fingerprint') != design.fingerprint
                or run.get('event_stream_hash') != kernel.to_dict()['event_stream_hash']
                or state['portable']['contract']['native_system']['system_fingerprint'] != design.fingerprint
                or world.get('years', horizon) != horizon
                or binding['science_config'].get('years', horizon) != horizon):
            raise ValueError('discrete policy requires the actual complete executed native design/horizon/event stream')


class NativeDiscretePolicySearch:
    def __init__(self, designs, *, loss_spec, seed=42, learning_rate=0.1,
                 distribution='categorical', logits=None, baseline=0.0):
        validate_loss_spec(loss_spec)
        if distribution not in {'categorical', 'bernoulli'}:
            raise ValueError('categorical or bernoulli distribution required')
        if (len(designs) < 2 or distribution == 'bernoulli' and len(designs) != 2
                or type(seed) is not int or not math.isfinite(learning_rate) or learning_rate <= 0
                or not math.isfinite(baseline)):
            raise ValueError('at least two designs, explicit seed, finite fixed baseline and positive learning rate required')
        self.designs = [SystemSpec.from_dict(d.to_dict() if isinstance(d, SystemSpec) else d) for d in designs]
        for design in self.designs:
            validate_system_spec(design).require_valid()
        if len({d.fingerprint for d in self.designs}) != len(self.designs):
            raise ValueError('duplicate designs would alias policy actions')
        self.loss_hash = loss_spec_sha256(loss_spec)
        self.seed, self.learning_rate, self.baseline = seed, float(learning_rate), float(baseline)
        self.distribution = distribution
        size = 1 if distribution == 'bernoulli' else len(self.designs)
        self.logits = torch.tensor([0.] * size if logits is None else logits, dtype=torch.float64, requires_grad=True)
        if self.logits.shape != (size,) or not torch.isfinite(self.logits).all():
            raise ValueError('finite distribution logits of the declared shape required')
        self.iteration, self.pending = 0, []

    def policy(self):
        if self.distribution == 'bernoulli':
            return torch.distributions.Bernoulli(logits=self.logits[0])
        return torch.distributions.Categorical(logits=self.logits)

    def action_log_probability(self, actions):
        values = torch.as_tensor(actions, dtype=torch.float64 if self.distribution == 'bernoulli' else torch.long)
        return self.policy().log_prob(values)

    def ask(self, count=2):
        if self.pending or type(count) is not int or count < 1:
            raise ValueError('positive draw count and no unfinished batch required')
        seed = int(digest({'seed': self.seed, 'iteration': self.iteration})[:15], 16)
        generator = torch.Generator().manual_seed(seed)
        if self.distribution == 'bernoulli':
            actions = (torch.rand(count, generator=generator, dtype=torch.float64) < self.policy().probs.detach()).long()
        else:
            actions = torch.multinomial(self.policy().probs.detach(), count, replacement=True, generator=generator)
        log_probs = self.action_log_probability(actions).detach().tolist()
        for index, (action, log_probability) in enumerate(zip(actions.tolist(), log_probs)):
            design = self.designs[action]
            identity = 'native-discrete-' + digest({'seed': self.seed, 'iteration': self.iteration,
                'draw': index, 'action': action, 'design': design.fingerprint, 'loss': self.loss_hash})[:20]
            suggestion = Suggestion(identity, design.to_dict(), self.iteration * count + index, 'discrete-policy')
            self.pending.append({'suggestion': suggestion.to_dict(), 'action': action,
                'log_probability': log_probability, 'rng_seed': seed, 'draw': index})
        return [Suggestion.from_dict(r['suggestion']) for r in self.pending]

    def tell(self, observations):
        if not self.pending or len(observations) != len(self.pending):
            raise ValueError('one observation per pending policy draw required')
        by_id = {o.suggestion_id: o for o in observations}
        if len(by_id) != len(observations):
            raise ValueError('duplicate discrete-policy observation')
        ordered = []
        for record in self.pending:
            suggestion = Suggestion.from_dict(record['suggestion'])
            observation = by_id.get(suggestion.suggestion_id)
            if (observation is None or observation.candidate != suggestion.candidate
                    or observation.metadata.get('world_backend') != 'native-research-world'
                    or observation.metadata.get('loss_spec_sha256') != self.loss_hash):
                raise ValueError('native policy candidate/loss/world binding mismatch')
            ordered.append(observation)
        report = {'schema': SCHEMA, 'method': 'native-discrete-reinforce-autograd', 'iteration': self.iteration,
            'distribution': self.distribution, 'loss_spec_sha256': self.loss_hash,
            'draws': clone(self.pending), 'observations': [o.to_dict() for o in ordered],
            'logits_before': self.logits.detach().tolist(), 'baseline': self.baseline,
            'gradient_target': 'expected complete native loss under declared discrete design distribution',
            'end_to_end_native_autograd': False,
            'feedback_scope': 'fresh full native executions, responsive fixed LLM; exact policy score, not pathwise native backprop'}
        if any(o.status != 'complete' or o.metadata.get('technical_failures') for o in ordered):
            report.update(status='not-updated-technical-failure', gradient=None)
        else:
            costs = torch.tensor([o.loss for o in ordered], dtype=torch.float64)
            if not torch.isfinite(costs).all():
                raise ValueError('finite actual native loss required')
            log_probability = self.action_log_probability([r['action'] for r in self.pending])
            if log_probability.detach().tolist() != [r['log_probability'] for r in self.pending]:
                raise ValueError('sampled log probabilities changed before update')
            score_loss = ((costs - self.baseline).detach() * log_probability).mean()
            gradient, = torch.autograd.grad(score_loss, self.logits)
            updated = self.logits.detach() - self.learning_rate * gradient
            if not torch.isfinite(updated).all():
                raise ValueError('nonfinite discrete-policy update')
            self.logits = updated.requires_grad_()
            report.update(status='updated', gradient=gradient.tolist(), losses=costs.tolist())
        report['logits_after'] = self.logits.detach().tolist()
        self.iteration += 1
        self.pending = []
        return report

    def state_dict(self):
        return {'schema': SCHEMA, 'designs': [d.to_dict() for d in self.designs],
            'loss_spec_sha256': self.loss_hash, 'seed': self.seed, 'learning_rate': self.learning_rate,
            'distribution': self.distribution, 'baseline': self.baseline, 'logits': self.logits.detach().tolist(),
            'iteration': self.iteration, 'pending': clone(self.pending)}

    @classmethod
    def from_state(cls, state, *, loss_spec):
        expected = {'schema', 'designs', 'loss_spec_sha256', 'seed', 'learning_rate',
                    'distribution', 'baseline', 'logits', 'iteration', 'pending'}
        if set(state) != expected or state['schema'] != SCHEMA or state['loss_spec_sha256'] != loss_spec_sha256(loss_spec):
            raise ValueError('discrete-policy checkpoint schema/loss mismatch')
        search = cls(state['designs'], loss_spec=loss_spec, seed=state['seed'],
            learning_rate=state['learning_rate'], distribution=state['distribution'],
            logits=state['logits'], baseline=state['baseline'])
        if type(state['iteration']) is not int or state['iteration'] < 0:
            raise ValueError('invalid policy iteration')
        search.iteration = state['iteration']
        if state['pending']:
            search.ask(len(state['pending']))
            if search.pending != state['pending']:
                raise ValueError('discrete-policy RNG/actions/log-probabilities/candidates changed')
        return search
