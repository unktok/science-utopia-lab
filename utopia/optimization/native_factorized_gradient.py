"""Exact score gradients for compositional, externally authored native designs.

Factors contain arbitrary caller-supplied code/protocol/parameter/wiring edits,
not a host institution catalog or a bank of complete SystemSpecs. Conditional
supports are explicit grammar, never inferred by dropping failed candidates.
Autograd differentiates joint action log probabilities, NOT the native world.
"""
from __future__ import annotations

import math

import torch

from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.loss import loss_spec_sha256, validate_loss_spec
from utopia.optimization.native_discrete_policy import verify_native_observation
from utopia.optimization.native_gradient import NativeGradientCampaign
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import apply_design_patch, clone, digest, make_patch

SCHEMA = 'scienceutopia.native-factorized-design-policy.v6'


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def factor_logit_size(factor):
    """One log-odds parameter for Bernoulli; one logit per categorical choice."""
    return 1 if factor['kind'] == 'bernoulli' else len(factor['choices'])


class FactorLogitError(ValueError):
    """Technical shape feedback only, never a proposed policy/value correction."""
    def __init__(self, factor, actual_shape, *, finite):
        self.details = {'factor_id': factor['id'], 'factor_kind': factor['kind'],
            'choice_count': len(factor['choices']), 'expected_shape': [factor_logit_size(factor)],
            'actual_shape': list(actual_shape), 'all_values_finite': finite,
            'authored_value_changed_by_host': False}
        super().__init__('finite logits of the declared factor shape required: factor '
            + repr(factor['id']) + ' (' + factor['kind'] + '), expected_shape='
            + repr(self.details['expected_shape']) + ', actual_shape=' + repr(list(actual_shape))
            + ', all_values_finite=' + str(finite))


class NativeFactorizedDesignSearch:
    """IID joint assignments -> atomic design edits -> actual native losses.

    Every reachable assignment is statically preflighted BEFORE any sampling.
    A malformed assignment rejects the entire declared grammar; no probability
    mass is silently removed, remapped, retried or conditioned on run success.
    Different assignments may compile to one design: their original latent
    assignments and exact joint log probabilities are retained independently.
    """
    def __init__(self, base_system, factors, *, loss_spec, design_provenance,
                 seed=42, learning_rate=.1, baseline=0., logits=None, max_assignments=4096):
        validate_loss_spec(loss_spec)
        if (type(seed) is not int or not _finite(learning_rate) or learning_rate <= 0
                or type(max_assignments) is not int or max_assignments < 1
                or not isinstance(design_provenance, dict) or not design_provenance
                or not (baseline == 'leave-one-out' or _finite(baseline))):
            raise ValueError('explicit provenance/seed, finite baseline or leave-one-out, positive learning rate/budget required')
        base_document = clone(base_system.to_dict() if isinstance(base_system, SystemSpec) else base_system)
        self.base = SystemSpec.from_dict(base_document)
        if self.base.to_dict() != base_document:
            raise ValueError('base design has unknown/noncanonical fields; no silent design remapping')
        validate_system_spec(self.base).require_valid()
        # Exercise full source/program validation even for an identity choice.
        # This transaction is validation-only and is never an authored edit.
        try:
            apply_design_patch(self.base, make_patch(self.base, [
                {'op': 'replace', 'path': '/metadata', 'value': clone(self.base.metadata)}]))
        except ValueError as error:
            if str(error) != 'design edit is a no-op':
                raise ValueError('invalid base design: ' + str(error)) from error
        self.factors, self.provenance = clone(factors), clone(design_provenance)
        if not isinstance(self.factors, list) or not self.factors:
            raise ValueError('nonempty ordered caller-authored factor list required')
        self.seed, self.learning_rate = seed, float(learning_rate)
        self.baseline = baseline if baseline == 'leave-one-out' else float(baseline)
        self.max_assignments, self.loss_hash = max_assignments, loss_spec_sha256(loss_spec)
        self._validate_factors()
        self.space_sha256 = digest(self._definition())
        self.policy_sha256 = digest(self._policy_definition())
        self.assignments = self._enumerate_assignments()
        for assignment in self.assignments:
            try:
                self.compile_assignment(assignment)
            except Exception as error:
                raise ValueError('entire factor grammar rejected: invalid declared assignment '
                    + str(assignment) + ': ' + str(error)) from error
        if logits is not None and set(logits) != {f['id'] for f in self.factors}:
            raise ValueError('logits must identify every declared factor exactly')
        self.logits = {}
        for factor in self.factors:
            size = factor_logit_size(factor)
            values = [0.] * size if logits is None else logits[factor['id']]
            value = torch.tensor(values, dtype=torch.float64, device='cpu', requires_grad=True)
            if value.shape != (size,) or not torch.isfinite(value).all():
                raise FactorLogitError(factor, value.shape, finite=bool(torch.isfinite(value).all()))
            self.logits[factor['id']] = value
        self.iteration, self.completed_draws, self.pending = 0, 0, []

    def _definition(self):
        return {'base_system': self.base.to_dict(), 'factors': clone(self.factors),
            'design_provenance': clone(self.provenance), 'max_assignments': self.max_assignments}

    def _policy_definition(self):
        return {'space_sha256': self.space_sha256, 'loss_spec_sha256': self.loss_hash,
            'seed': self.seed, 'learning_rate': self.learning_rate, 'baseline': self.baseline}

    def _validate_factors(self):
        earlier = {}
        for factor in self.factors:
            if (not isinstance(factor, dict) or set(factor) - {'id', 'kind', 'choices', 'support'}
                    or not {'id', 'kind', 'choices'} <= set(factor)
                    or not isinstance(factor['id'], str) or not factor['id'] or factor['id'] in earlier
                    or factor['kind'] not in ('categorical', 'bernoulli')
                    or not isinstance(factor['choices'], list) or len(factor['choices']) < 2
                    or factor['kind'] == 'bernoulli' and len(factor['choices']) != 2):
                raise ValueError('unique factor ID, categorical/two-way Bernoulli and explicit choices required')
            choices = []
            for choice in factor['choices']:
                if (not isinstance(choice, dict) or set(choice) != {'id', 'operations', 'provenance'}
                        or not isinstance(choice['id'], str) or not choice['id'] or choice['id'] in choices
                        or not isinstance(choice['operations'], list)
                        or not isinstance(choice['provenance'], dict) or not choice['provenance']):
                    raise ValueError('each free choice needs unique ID, exact edit operations and explicit provenance')
                choices.append(choice['id'])
            if 'support' in factor:
                if not isinstance(factor['support'], list) or not factor['support']:
                    raise ValueError('conditional support must be a nonempty explicit rule list')
                for rule in factor['support']:
                    if (not isinstance(rule, dict) or set(rule) != {'when', 'allow'}
                            or not isinstance(rule['when'], dict) or not set(rule['when']) <= set(earlier)
                            or any(value not in earlier[key] for key, value in rule['when'].items())
                            or not isinstance(rule['allow'], list) or not rule['allow']
                            or len(set(rule['allow'])) != len(rule['allow']) or not set(rule['allow']) <= set(choices)):
                        raise ValueError('conditional support may reference only known earlier choices and nonempty current support')
            earlier[factor['id']] = choices

    def _support(self, factor, prefix):
        choices = [c['id'] for c in factor['choices']]
        if 'support' not in factor:
            return choices
        matches = [r for r in factor['support'] if all(prefix.get(key) == value for key, value in r['when'].items())]
        if len(matches) != 1:
            raise ValueError('conditional support must cover each reachable prefix exactly once: ' + str(prefix))
        return [choice for choice in choices if choice in matches[0]['allow']]

    def _enumerate_assignments(self):
        prefixes = [{}]
        for factor in self.factors:
            result = []
            for prefix in prefixes:
                for choice in self._support(factor, prefix):
                    result.append({**prefix, factor['id']: choice})
                    if len(result) > self.max_assignments:
                        raise ValueError('declared factor support exceeds explicit preflight budget; no support was dropped')
            prefixes = result
        return prefixes

    def compile_assignment(self, assignment):
        if set(assignment) != {f['id'] for f in self.factors}:
            raise ValueError('assignment must identify every factor exactly')
        prefix, operations = {}, []
        for factor in self.factors:
            choice_id = assignment[factor['id']]
            if choice_id not in self._support(factor, prefix):
                raise ValueError('assignment lies outside the explicitly declared conditional support')
            choice = next(c for c in factor['choices'] if c['id'] == choice_id)
            operations.extend(clone(choice['operations']))
            prefix[factor['id']] = choice_id
        if not operations:
            return self.base, None
        patch = make_patch(self.base, operations, rationale='caller-authored factor edits applied atomically')
        try:
            candidate = apply_design_patch(self.base, patch)
        except ValueError as error:
            if str(error) != 'design edit is a no-op':
                raise
            candidate = self.base  # A legal identity map, NOT remapping an invalid action.
        return candidate, patch

    def _log_probabilities(self, factor, prefix):
        allowed, logits = self._support(factor, prefix), self.logits[factor['id']]
        if len(allowed) == 1:
            return allowed, (logits[0] * 0).reshape(1)
        if factor['kind'] == 'bernoulli':
            return allowed, torch.stack((-torch.nn.functional.softplus(logits[0]),
                -torch.nn.functional.softplus(-logits[0])))
        indices = [i for i, c in enumerate(factor['choices']) if c['id'] in allowed]
        return allowed, torch.log_softmax(logits[indices], dim=0)

    def action_log_probability(self, assignments):
        if not assignments:
            raise ValueError('at least one explicit joint assignment required')
        terms = []
        for assignment in assignments:
            if set(assignment) != {f['id'] for f in self.factors}:
                raise ValueError('joint assignment fields differ')
            prefix, logq = {}, []
            for factor in self.factors:
                allowed, log_probabilities = self._log_probabilities(factor, prefix)
                selected = assignment[factor['id']]
                if selected not in allowed:
                    raise ValueError('zero-support joint action cannot receive a remapped likelihood')
                logq.append(log_probabilities[allowed.index(selected)])
                prefix[factor['id']] = selected
            terms.append(torch.stack(logq).sum())
        return torch.stack(terms)

    def _draw_batch(self, count):
        if digest(self._definition()) != self.space_sha256:
            raise ValueError('factor programs/provenance changed after policy definition')
        if digest(self._policy_definition()) != self.policy_sha256:
            raise ValueError('factorized policy seed/loss/learning settings changed')
        rng_seed = int(digest({'seed': self.seed, 'iteration': self.iteration})[:15], 16)
        generator = torch.Generator(device='cpu').manual_seed(rng_seed)
        records = []
        for draw in range(count):
            prefix, trace = {}, []
            for factor in self.factors:
                allowed, log_probabilities = self._log_probabilities(factor, prefix)
                selected_index = int(torch.multinomial(log_probabilities.detach().exp(), 1, generator=generator))
                selected = allowed[selected_index]
                trace.append({'factor_id': factor['id'], 'kind': factor['kind'], 'allowed_choices': allowed,
                    'selected_choice': selected, 'conditional_log_probability': float(log_probabilities[selected_index].detach())})
                prefix[factor['id']] = selected
            candidate, patch = self.compile_assignment(prefix)
            logq = float(self.action_log_probability([prefix])[0].detach())
            identity = 'native-factorized-' + digest({'space': self.space_sha256, 'loss': self.loss_hash,
                'seed': self.seed, 'iteration': self.iteration, 'draw': draw, 'assignment': prefix,
                'candidate': candidate.fingerprint, 'policy': self.policy_sha256})[:20]
            suggestion = Suggestion(identity, candidate.to_dict(), self.completed_draws + draw, 'factorized-native-policy')
            records.append({'suggestion': suggestion.to_dict(), 'assignment': prefix, 'patch': patch,
                'factor_trace': trace, 'joint_log_probability': logq, 'rng_seed': rng_seed, 'draw': draw,
                'space_sha256': self.space_sha256, 'policy_sha256': self.policy_sha256})
        return records

    def ask(self, count=2):
        if self.pending or type(count) is not int or count < 1 or self.baseline == 'leave-one-out' and count < 2:
            raise ValueError('positive IID batch, no pending draws, and at least two draws for leave-one-out required')
        self.pending = self._draw_batch(count)
        return [Suggestion.from_dict(r['suggestion']) for r in self.pending]

    def tell(self, observations):
        if not self.pending or len(observations) != len(self.pending):
            raise ValueError('one full native observation per pending joint assignment required')
        if self._draw_batch(len(self.pending)) != self.pending:
            raise ValueError('pending actions/log probabilities/designs/RNG changed before update')
        by_id = {o.suggestion_id: o for o in observations}
        if len(by_id) != len(observations):
            raise ValueError('duplicate factorized observation')
        ordered = []
        for record in self.pending:
            suggestion = Suggestion.from_dict(record['suggestion'])
            obs = by_id.get(suggestion.suggestion_id)
            if (obs is None or obs.candidate != suggestion.candidate
                    or obs.metadata.get('world_backend') != 'native-research-world'
                    or obs.metadata.get('loss_spec_sha256') != self.loss_hash):
                raise ValueError('factorized observation candidate/native-world/loss binding mismatch')
            ordered.append(obs)
        report = {'schema': SCHEMA, 'method': 'conditional-factorized-native-score-autograd',
            'space_sha256': self.space_sha256, 'policy_sha256': self.policy_sha256,
            'loss_spec_sha256': self.loss_hash, 'iteration': self.iteration,
            'draws': clone(self.pending), 'observations': [o.to_dict() for o in ordered],
            'logits_before': {key: value.detach().tolist() for key, value in self.logits.items()},
            'baseline_policy': self.baseline, 'sampling': 'iid joint ancestral factor draws',
            'gradient_target': 'expected full native loss under the declared conditional factor grammar',
            'pathwise_native_or_llm_derivative': False, 'llm_weight_training': False,
            'unbiasedness_scope': 'Requires a complete defined native cost for every supported action; technical failures define no conditional-on-success objective.'}
        if any(o.status != 'complete' or o.metadata.get('technical_failures') for o in ordered):
            report.update(status='not-updated-technical-failure', gradient=None, losses=[o.loss for o in ordered])
        else:
            if any(not _finite(o.loss) for o in ordered):
                raise ValueError('complete native losses must be finite real numbers')
            costs = torch.tensor([o.loss for o in ordered], dtype=torch.float64, device='cpu')
            baseline = ((costs.sum() - costs) / (len(costs)-1) if self.baseline == 'leave-one-out'
                else torch.full_like(costs, self.baseline))
            logq = self.action_log_probability([r['assignment'] for r in self.pending])
            parameters = tuple(self.logits.values())
            score_loss = ((costs - baseline).detach() * logq).mean()
            gradients = torch.autograd.grad(score_loss, parameters)
            score_terms = []
            for i in range(len(costs)):
                term = torch.autograd.grad(self.action_log_probability([self.pending[i]['assignment']])[0], parameters)
                score_terms.append({key: ((costs[i] - baseline[i]) * value).detach().tolist()
                    for key, value in zip(self.logits, term)})
            updated = {key: value.detach() - self.learning_rate * grad
                for (key, value), grad in zip(self.logits.items(), gradients)}
            if any(not torch.isfinite(value).all() for value in updated.values()):
                raise ValueError('nonfinite factorized policy update')
            self.logits = {key: value.requires_grad_() for key, value in updated.items()}
            report.update(status='updated', losses=costs.tolist(), baselines=baseline.tolist(),
                gradient={key: value.tolist() for key, value in zip(self.logits, gradients)},
                per_draw_score_terms=score_terms, all_equal_costs=bool((costs == costs[0]).all()),
                all_zero_costs=bool((costs == 0).all()),
                distinct_sampled_assignments=len({digest(r['assignment']) for r in self.pending}),
                distinct_sampled_systems=len({SystemSpec.from_dict(r['suggestion']['candidate']).fingerprint for r in self.pending}),
                sampling_note='Equal costs imply no comparative evidence; fixed-baseline finite samples may still have nonzero score noise. LOO equal-cost advantages are exactly zero.')
        report['logits_after'] = {key: value.detach().tolist() for key, value in self.logits.items()}
        self.completed_draws += len(self.pending)
        self.iteration += 1
        self.pending = []
        return report

    def state_dict(self):
        return {'schema': SCHEMA, **self._definition(), 'space_sha256': self.space_sha256,
            'policy_sha256': self.policy_sha256,
            'loss_spec_sha256': self.loss_hash, 'seed': self.seed, 'learning_rate': self.learning_rate,
            'baseline': self.baseline, 'logits': {key: value.detach().tolist() for key, value in self.logits.items()},
            'iteration': self.iteration, 'completed_draws': self.completed_draws, 'pending': clone(self.pending)}

    @classmethod
    def from_state(cls, state, *, loss_spec):
        expected = {'schema', 'base_system', 'factors', 'design_provenance', 'max_assignments', 'space_sha256', 'policy_sha256',
            'loss_spec_sha256', 'seed', 'learning_rate', 'baseline', 'logits', 'iteration', 'completed_draws', 'pending'}
        if set(state) != expected or state['schema'] != SCHEMA or state['loss_spec_sha256'] != loss_spec_sha256(loss_spec):
            raise ValueError('factorized policy state schema/loss differs')
        search = cls(state['base_system'], state['factors'], loss_spec=loss_spec,
            design_provenance=state['design_provenance'], max_assignments=state['max_assignments'],
            seed=state['seed'], learning_rate=state['learning_rate'], baseline=state['baseline'], logits=state['logits'])
        if (search.space_sha256 != state['space_sha256'] or search.policy_sha256 != state['policy_sha256']
                or any(type(state[key]) is not int or state[key] < 0
                for key in ('iteration', 'completed_draws'))):
            raise ValueError('factorized definition/provenance/settings/iteration changed')
        search.iteration, search.completed_draws = state['iteration'], state['completed_draws']
        if state['pending']:
            search.ask(len(state['pending']))
            if search.pending != state['pending']:
                raise ValueError('factorized pending assignments/support/log probabilities/designs/RNG changed')
        return search


class NativeFactorizedGradientCampaign(NativeGradientCampaign):
    """Existing durable one-writer campaign plus factorized replay/checkpoints."""
    def _restore_search(self, state):
        return NativeFactorizedDesignSearch.from_state(state, loss_spec=self.loss_spec)

    def _validate(self):
        search = super()._validate()
        # The parent replays losses and exact updates. Verify original native
        # world/checkpoint/model/source/seed evidence before returning a usable
        # state or before its inherited advance() persists the next update.
        values = [value for report in self.state['reports'] for value in report['observations']]
        values.extend(self.state['observations'])
        for value in values:
            verify_native_observation(Observation.from_dict(value), self.binding['world'], self.seeds)
        return search
