"""Opt-in bounded autonomous search over the existing native campaigns.

The controller adds no optimizer, merit veto, native retry or source executor.
Every generated definition is committed by v7/v13 before the native evaluation.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_jobs import METRICS, validate_job_request
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

REQUEST_SCHEMA = 'scienceutopia.native-search-request.v14'
PLAN_SCHEMA = 'scienceutopia.native-search-plan.v14'
PROGRESS_SCHEMA = 'scienceutopia.native-search-progress.v14'
STRATEGY = 'local-llm-free-vocabulary'


def validate_search_request(request):
    fields = {'schema', 'initial_system', 'loss_spec', 'seed', 'years', 'method', 'native_budget', 'designer'}
    if not isinstance(request, dict) or set(request) != fields or request['schema'] != REQUEST_SCHEMA:
        raise ValueError('exact native-search-request.v14 fields required')
    # Reuse existing native safety, development-seed, code-image and loss checks.
    validate_job_request({'parent_system': request['initial_system'], 'system': request['initial_system'],
        **{k: request[k] for k in ('loss_spec', 'seed', 'years')}},
        measured_metrics=METRICS | {'native.accepted_peer_score_sum', 'native.accepted_unreviewed_decisions'})
    if request['method'] not in {'blackbox', 'nested-lr'}:
        raise ValueError('search method must be blackbox or nested-lr')
    budget = request['native_budget']
    if type(budget) is not int or not 1 <= budget <= 8:
        raise ValueError('bounded native budget must be 1..8')
    if request['method'] == 'nested-lr' and budget != 4:
        raise ValueError('nested-lr requires exactly four slots: unchanged v13 2→1→1')
    designer = request['designer']
    if (not isinstance(designer, dict) or set(designer) != {'model', 'max_attempts', 'max_tokens'}
            or designer['model'] != 'qwen3:8b'
            or type(designer['max_attempts']) is not int or not 1 <= designer['max_attempts'] <= 3
            or type(designer['max_tokens']) is not int or not 512 <= designer['max_tokens'] <= 8192):
        raise ValueError('fixed local qwen3:8b designer and bounded attempts/tokens required')
    if len(json.dumps(request, allow_nan=False).encode()) > 512_000:
        raise ValueError('search request exceeds byte budget')


def validate_provider_binding(binding):
    required = {'model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years', 'image_id'}
    if (not isinstance(binding, dict) or set(binding) != required or binding['model'] != 'qwen3:8b'
            or any(not isinstance(binding[k], str) or not binding[k] for k in ('model_digest', 'corpus_sha256'))
            or not isinstance(binding['dataset_identity'], dict) or not binding['dataset_identity']
            or type(binding['corpus_years']) is not int or binding['corpus_years'] != 4
            or not isinstance(binding['image_id'], str)
            or not re.fullmatch(r'sha256:[a-f0-9]{64}', binding['image_id'])):
        raise ValueError('operator-owned pinned local model/corpus/dataset/four-year horizon/image binding required')
    digest(binding)


def make_search_plan(request, *, source_commit, provider_binding):
    validate_search_request(request)
    validate_provider_binding(provider_binding)
    if not isinstance(source_commit, str) or not re.fullmatch(r'[a-f0-9]{40}', source_commit):
        raise ValueError('clean pinned source commit required')
    return {'schema': PLAN_SCHEMA, 'request': clone(request), 'request_sha256': digest(request),
        'source_commit': source_commit, 'provider_binding': clone(provider_binding),
        'stage_counts': [1] * request['native_budget'] if request['method'] == 'blackbox' else [2, 1, 1],
        'generator_calls': request['native_budget'] if request['method'] == 'blackbox' else 2,
        'maximum_designer_provider_attempts': (request['native_budget'] if request['method'] == 'blackbox' else 2)
            * request['designer']['max_attempts'],
        'native_retry_policy': 'none; existing exact native checkpoint/response replay only',
        'failed_generation_policy': 'consume scheduled slots with null loss; no replacement',
        'objective_policy': 'declared LossSpec; technical validity separate; no merit/promotion veto',
        'origin': 'explicit-local-UI-compute-consent', 'model_weights_trained': False}


class NativeSearchController:
    """Single-writer caller owns locking; readers validate exact persisted state."""
    plan_builder = staticmethod(make_search_plan)

    def __init__(self, directory, *, plan, plan_sha256):
        self.directory = Path(directory)
        expected = self.plan_builder(plan['request'], source_commit=plan['source_commit'],
            provider_binding=plan['provider_binding'])
        if plan != expected or digest(plan) != plan_sha256:
            raise ValueError('immutable search plan binding changed')
        self.plan, self.plan_sha256 = clone(plan), plan_sha256
        path = self.directory / 'plan.json'
        if path.exists():
            if json.loads(path.read_text()) != plan:
                raise ValueError('saved search plan changed')
        else:
            write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
        request = plan['request']
        self.request = clone(request)
        world = {'source_commit': plan['source_commit'], **clone(plan['provider_binding']),
            'request_sha256': plan['request_sha256'], 'search_plan_sha256': plan_sha256,
            'years': request['years'], 'population': 'five-independent-balanced-researchers',
            'origin': plan['origin']}
        common = dict(initial_system=SystemSpec.from_dict(request['initial_system']),
            loss_spec=request['loss_spec'], seeds=[request['seed']], world_binding=world, seed=request['seed'])
        if request['method'] == 'blackbox':
            self.campaign = NativeAdaptiveDesignCampaign(self.directory / 'campaign', **common,
                mode='blackbox', strategies={STRATEGY: {'kind': 'local-llm-free-vocabulary',
                    'model': request['designer']['model'], 'plan_sha256': plan_sha256}})
        else:
            self.campaign = NativeNestedDesignCampaign(self.directory / 'campaign', **common)
        records = self.campaign.state['records']
        pending = self.campaign.state['pending']
        if (len(records) > len(plan['stage_counts'])
                or any(r['request']['count'] != plan['stage_counts'][i] for i, r in enumerate(records))
                or pending and (len(records) == len(plan['stage_counts'])
                    or pending['request']['count'] != plan['stage_counts'][len(records)])):
            raise ValueError('search campaign exceeded or changed scheduled slots')

    @property
    def complete(self):
        return len(self.campaign.state['records']) == len(self.plan['stage_counts'])

    def advance(self, *, simulation_factory, generator):
        if self.complete:
            raise ValueError('finite autonomous native budget already exhausted')
        def bounded_generation(request):
            try:
                return generator(request)
            except Exception as error:
                # The trusted adapter owns its finite provider-attempt journal.
                # Unexpected callback failures also consume this authored stage.
                return {'generation_failure': {'type': type(error).__name__,
                    'message': str(error)[:2000], 'loss': None}}
        if self.request['method'] == 'blackbox':
            return self.campaign.advance(simulation_factory=simulation_factory,
                generators={STRATEGY: bounded_generation}, count=1)
        return self.campaign.advance(simulation_factory=simulation_factory, generator=bounded_generation)

    def projection(self, *, search_id, status, errors=()):
        state = self.campaign.state
        records = clone(state['records'])
        pending = clone(state['pending'])
        all_records = records + ([pending] if pending else [])
        observations = [{'suggestion': d['suggestion'], 'observation': o}
            for r in all_records for d, o in zip(r['draws'], r['observations'])]
        valid = [o for o in observations if o['suggestion'] and o['observation']
            and o['observation']['status'] == 'complete'
            and not o['observation']['metadata'].get('technical_failures')]
        best_loss = min((o['observation']['loss'] for o in valid), default=None)
        ties = [o for o in valid if o['observation']['loss'] == best_loss]
        consumed = sum(r['request']['count'] for r in records)
        record_errors = [{'stage_index': i, 'stage': r.get('stage', 'generation-' + str(i)),
                'generation_error': r['generation_error'],
                'technical_failures': [o['metadata'].get('technical_failures', []) for o in r['observations'] if o],
                'draw_errors': [d['technical_error'] for d in r['draws'] if d['technical_error']]}
            for i, r in enumerate(all_records) if r['generation_error']
                or any(d['technical_error'] for d in r['draws'])
                or any(o and o['metadata'].get('technical_failures') for o in r['observations'])]
        return {'schema': PROGRESS_SCHEMA, 'search_id': search_id, 'status': status,
            'request': clone(self.request), 'request_sha256': self.plan['request_sha256'],
            'source_commit': self.plan['source_commit'], 'plan_sha256': self.plan_sha256,
            'method': self.request['method'], 'native_budget': self.request['native_budget'],
            'stage': 'complete' if self.complete else (pending or {}).get('stage',
                'generation-' + str(len(records)) if self.request['method'] == 'blackbox'
                else ['initial-batch', 'updated-proposal', 'redesign'][len(records)]),
            'records': records, 'pending': pending, 'observations': observations,
            'current': ({'suggestion': all_records[-1]['draws'][len(all_records[-1]['observations']) - 1]['suggestion'],
                'observation': all_records[-1]['observations'][-1]}
                if all_records and all_records[-1]['observations'] else None),
            'best': {'loss': best_loss, 'ties': ties, 'incumbent': ties[0] if ties else None},
            'errors': record_errors + list(errors),
            'budget': {'scheduled': self.request['native_budget'], 'consumed': consumed,
                'native_observations': sum(o['observation'] is not None for o in observations),
                'remaining': self.request['native_budget'] - consumed},
            'immutable_plan': clone(self.plan), 'model_weights_trained': False,
            'same_society_migration': False, 'seed_role': 'development'}
