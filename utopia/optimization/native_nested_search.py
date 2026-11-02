"""Finite free-vocabulary / conditional-weight / free-redesign native search.

Generated code remains data for the isolated native executor. Only the declared
conditional design likelihood is differentiated, never source, LLM or world.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import torch

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from .native_adaptive_search import GeneratedMixedDesign, expectation_compatibility
from .native_discrete_policy import verify_native_observation
from .native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.native-nested-search.v13'
STAGES = ('initial-batch', 'updated-proposal', 'redesign')
COUNTS = (2, 1, 1)


class NativeNestedDesignCampaign:
    """A fixed four-slot arm; every saved stage is independently replayable.

    G0 gets two IID draws and exactly one LOO LR update. The next singleton
    uses that exact vocabulary and its resulting weights without another tell.
    G1 is externally authored from all own feedback, with no implicit weight,
    coordinate, gradient or control-variate transport into its new vocabulary.
    """
    def __init__(self, directory, *, initial_system, loss_spec, seeds,
                 world_binding, seed=42, learning_rate=.1):
        validate_loss_spec(loss_spec)
        if (type(seed) is not int or not seeds or any(type(s) is not int for s in seeds)
                or len(set(seeds)) != len(seeds) or not isinstance(world_binding, dict)
                or any(not world_binding.get(k) for k in ('source_commit', 'model_digest', 'corpus_sha256'))
                or type(learning_rate) not in (int, float) or not math.isfinite(learning_rate)
                or learning_rate <= 0):
            raise ValueError('explicit source/model/corpus/seeds and finite positive learning rate required')
        self.directory, self.initial, self.loss = Path(directory), initial_system, clone(loss_spec)
        self.path = self.directory / 'native-nested-state.json'
        self.binding = {'initial_system': initial_system.to_dict(), 'loss_spec': clone(loss_spec),
            'world': clone(world_binding), 'seeds': list(seeds), 'seed': seed,
            'learning_rate': float(learning_rate), 'stages': list(STAGES),
            'stage_counts': list(COUNTS), 'planned_native_world_budget': 4,
            'estimator': 'leave-one-out-conditional-likelihood-ratio',
            'weight_transport': 'exact-G0-only; G1-explicit-definition-reset'}
        self.binding_sha256 = digest(self.binding)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            self._validate()
        else:
            self.state = {'schema': SCHEMA, 'binding': clone(self.binding), 'records': [], 'pending': None}
            self._save()

    def _save(self):
        write_json_atomic(self.path, self.state, sort_keys=True, allow_nan=False)

    @staticmethod
    def _valid(observation):
        return bool(observation and observation['status'] == 'complete'
                    and not observation['metadata'].get('technical_failures'))

    def _request(self, records):
        index = len(records)
        if index >= len(STAGES):
            raise ValueError('finite nested native budget already exhausted')
        observations = [{'suggestion': d['suggestion'], 'observation': o}
            for r in records for d, o in zip(r['draws'], r['observations'])
            if d['suggestion'] is not None and o is not None]
        valid = [v for v in observations if self._valid(v['observation'])]
        best = min((v['observation']['loss'] for v in valid), default=None)
        ties = [v for v in valid if v['observation']['loss'] == best]
        incumbent = ties[0] if ties else None
        return {'schema': SCHEMA + '.request', 'stage': STAGES[index],
            'generation': 1 if index == 2 else 0, 'count': COUNTS[index],
            'external_authoring': index != 1,
            'parent_system': incumbent['suggestion']['candidate'] if incumbent else self.initial.to_dict(),
            'based_on_observation_id': incumbent['observation']['observation_id'] if incumbent else None,
            'incumbent_ties': [v['observation']['observation_id'] for v in ties],
            'parent_selection': 'earliest display representative; all exact ties retained',
            'observations': observations, 'history': clone(records),
            'loss_spec': clone(self.loss), 'world_binding': clone(self.binding['world']),
            'rng_seed': int(digest({'seed': self.binding['seed'], 'stage': STAGES[index]})[:15], 16),
            'binding_sha256': digest(self.binding), 'history_sha256': digest(records),
            'proposal_start': sum(COUNTS[:index]),
            'distribution_state_policy': 'reuse exact G0 saved update' if index == 1 else
                'fresh explicitly authored vocabulary; no implicit previous-weight/control transport'}

    def _mixed(self, record):
        source = record
        if record['stage'] == 'updated-proposal':
            source = record['request']['history'][0]
        mixed = GeneratedMixedDesign(SystemSpec.from_dict(source['request']['parent_system']),
            record['definition'], loss_spec=self.loss, seed=record['request']['rng_seed'],
            learning_rate=self.binding['learning_rate'],
            single_draw_blackbox=record['request']['count'] == 1)
        if record['stage'] == 'updated-proposal':
            weights = source['report']['weights_after']
            if (set(weights) != {'logits', 'continuous_mean'}
                    or set(weights['logits']) != set(mixed.weights()['logits'])
                    or len(weights['continuous_mean']) != len(mixed.coordinates)):
                raise ValueError('saved update incompatible with exact G0 vocabulary')
            with torch.no_grad():
                for key, parameter in (mixed.policy.logits.items() if mixed.policy else []):
                    parameter.copy_(torch.tensor(weights['logits'][key], dtype=torch.float64))
                mixed.mean.copy_(torch.tensor(weights['continuous_mean'], dtype=torch.float64))
            if mixed.weights() != weights:
                raise ValueError('saved updated distribution changed')
        return mixed

    def _compile(self, record):
        if record['stage'] == 'updated-proposal' and record['request']['history'][0]['generation_error']:
            raise ValueError('G0 vocabulary unavailable; updated-proposal slot consumed without replacement')
        mixed = self._mixed(record)
        draws = mixed.draw(record['request']['count'], version_sha256=record['draw_version_sha256'],
            proposal_start=record['request']['proposal_start'],
            based_on=record['request']['based_on_observation_id'])
        return mixed, draws

    def _finish(self, record):
        if record['generation_error']:
            return {'status': 'invalid-generated-vocabulary', 'gradient': None,
                'weights_before': None, 'weights_after': None, 'losses': [None] * record['request']['count'],
                'pathwise_native_or_llm_or_source_derivative': False}
        mixed, _ = self._compile(record)
        before = mixed.weights()
        if record['stage'] != 'initial-batch':
            return {'status': 'forward-only-observed' if all(self._valid(o) for o in record['observations'])
                    else 'forward-only-technical-failure', 'gradient': None,
                'weights_before': before, 'weights_after': before,
                'losses': [o['loss'] if o else None for o in record['observations']],
                'no_update_reason': 'fixed budget; singleton is not an LR/LOO estimator',
                'compatibility_sha256': expectation_compatibility(mixed),
                'pathwise_native_or_llm_or_source_derivative': False}
        try:
            report = mixed.update(record['draws'], record['observations'], score=True)
        except (ValueError, RuntimeError, OverflowError) as error:
            # Never turn failed/nonfinite gradient machinery into a replacement
            # native draw, numerical loss or an invented policy update.
            report = {'status': 'not-updated-estimator-failure', 'gradient': None,
                'weights_before': before, 'weights_after': before,
                'losses': [o['loss'] if o else None for o in record['observations']],
                'estimator_error': self._error(error),
                'pathwise_native_or_llm_or_source_derivative': False}
        report['compatibility_sha256'] = expectation_compatibility(mixed)
        report['next_distribution'] = 'exact weights_after; unchanged if update invalid or no coordinates'
        return report

    @staticmethod
    def _error(error):
        return {'type': type(error).__name__, 'message': str(error)[:2000], 'loss': None}

    def _check_observation(self, value, draw):
        if draw['suggestion'] is None:
            if value is not None:
                raise ValueError('invalid draw cannot receive numeric evidence')
            return
        observation = Observation.from_dict(value)
        suggestion = draw['suggestion']
        evaluated = evaluate_loss(self.loss, observation.metadata.get('measurements', []))
        if (observation.suggestion_id != suggestion['suggestion_id']
                or observation.candidate != suggestion['candidate']
                or observation.metadata.get('world_backend') != 'native-research-world'
                or observation.metadata.get('loss_spec_sha256') != loss_spec_sha256(self.loss)
                or observation.metadata.get('loss_evaluation') != evaluated
                or observation.loss != (evaluated['loss'] if evaluated['status'] == 'complete' else None)
                or (observation.status == 'complete') != (evaluated['status'] == 'complete')):
            raise ValueError('native observation/measurement/loss/design changed')
        verify_native_observation(observation, self.binding['world'], self.binding['seeds'])

    def _validate(self):
        if (set(self.state) != {'schema', 'binding', 'records', 'pending'}
                or self.state['schema'] != SCHEMA or self.state['binding'] != self.binding
                or digest(self.binding) != self.binding_sha256
                or self.loss != self.binding['loss_spec']
                or self.initial.to_dict() != self.binding['initial_system']
                or len(self.state['records']) > len(STAGES)):
            raise ValueError('nested campaign binding or finite budget changed')
        records = []
        for complete, record in [(True, r) for r in self.state['records']] + (
                [(False, self.state['pending'])] if self.state['pending'] is not None else []):
            expected_keys = {'stage', 'generation', 'request', 'request_sha256', 'definition',
                'version_sha256', 'draw_version_sha256', 'generation_error', 'draws', 'observations',
                'report', 'generated', 'compiled'}
            request = self._request(records)
            if (set(record) != expected_keys or request != record['request']
                    or record['request_sha256'] != digest(request)
                    or record['stage'] != request['stage'] or record['generation'] != request['generation']
                    or type(record['generated']) is not bool or type(record['compiled']) is not bool):
                raise ValueError('nested exact stage/history/parent/request changed')
            if not record['generated']:
                if (record['definition'] is not None or record['version_sha256'] is not None
                        or record['draw_version_sha256'] is not None or record['compiled']
                        or record['draws'] or record['observations'] or record['generation_error'] or complete):
                    raise ValueError('unbound vocabulary cannot have execution evidence')
            else:
                if record['stage'] == 'updated-proposal':
                    g0 = records[0]
                    if record['definition'] != g0['definition'] or record['version_sha256'] != g0['version_sha256']:
                        raise ValueError('updated proposal must preserve exact G0 definition/version')
                elif record['version_sha256'] != digest({'request': record['request_sha256'],
                                                       'definition': record['definition']}):
                    raise ValueError('generated vocabulary/version changed')
                if record['draw_version_sha256'] != digest({'vocabulary': record['version_sha256'],
                        'request': record['request_sha256']}):
                    raise ValueError('stage-specific draw namespace changed')
                if not record['compiled']:
                    if record['draws'] or record['observations'] or record['generation_error'] or complete:
                        raise ValueError('uncompiled vocabulary cannot have execution evidence')
                elif record['generation_error']:
                    if record['draws'] or record['observations']:
                        raise ValueError('invalid vocabulary cannot contain native draws or observations')
                    try:
                        self._compile(record)
                    except Exception as error:
                        if record['generation_error'] != self._error(error):
                            raise ValueError('generation technical error changed') from error
                    else:
                        raise ValueError('valid vocabulary relabelled invalid')
                elif self._compile(record)[1] != record['draws']:
                    raise ValueError('draw/definition/updated-weights/likelihood changed')
            if len(record['observations']) > len(record['draws']):
                raise ValueError('too many native observations')
            for draw, observation in zip(record['draws'], record['observations']):
                self._check_observation(observation, draw)
            if complete:
                if not record['generation_error'] and len(record['observations']) != len(record['draws']):
                    raise ValueError('complete stage requires every scheduled observation')
                if record['report'] != self._finish(record):
                    raise ValueError('nested estimator/update or forward-only receipt changed')
                records.append(record)
            elif record['report'] is not None:
                raise ValueError('pending stage already has a report')

    def advance(self, *, simulation_factory, generator):
        """Consume one fixed stage, or leave its exact external request pending."""
        self._validate()
        record = self.state['pending']
        if record is None:
            request = self._request(self.state['records'])
            record = {'stage': request['stage'], 'generation': request['generation'],
                'request': request, 'request_sha256': digest(request), 'definition': None,
                'version_sha256': None, 'draw_version_sha256': None,
                'generation_error': None, 'draws': [], 'observations': [], 'report': None,
                'generated': False, 'compiled': False}
            self.state['pending'] = record
            self._save()
        if not record['generated']:
            if record['stage'] == 'updated-proposal':
                g0 = self.state['records'][0]
                definition, version = clone(g0['definition']), g0['version_sha256']
            else:
                definition = generator(clone(record['request']))
                version = digest({'request': record['request_sha256'], 'definition': definition})
            record.update(definition=definition, version_sha256=version, generated=True,
                draw_version_sha256=digest({'vocabulary': version, 'request': record['request_sha256']}))
            self._save()
        if not record['compiled']:
            try:
                _, record['draws'] = self._compile(record)
            except Exception as error:
                record['generation_error'] = self._error(error)
            record['compiled'] = True
            self._save()
        for draw in record['draws'][len(record['observations']):]:
            observation = (evaluate_native_suggestion(Suggestion.from_dict(draw['suggestion']),
                seeds=self.binding['seeds'], simulation_factory=simulation_factory,
                loss_spec=self.loss).to_dict() if draw['suggestion'] is not None else None)
            self._check_observation(observation, draw)
            record['observations'].append(observation)
            self._save()
        record['report'] = self._finish(record)
        self.state['records'].append(record)
        self.state['pending'] = None
        self._save()
        return clone(record)
