"""Opt-in staged authoring over unchanged native blackbox/nested campaigns."""
from __future__ import annotations

import json
import re

from .native_search_v14 import NativeSearchController, validate_provider_binding
from .native_search_v14 import validate_search_request as validate_legacy_request
from .native_search_jobs_v14 import NativeSearchQueue
from utopia.system.design_patch import clone, digest

REQUEST_SCHEMA = 'scienceutopia.native-search-request.v15'
PLAN_SCHEMA = 'scienceutopia.native-search-plan.v15'
PROGRESS_SCHEMA = 'scienceutopia.native-search-progress.v15'


def validate_search_request(request):
    fields = {'schema', 'initial_system', 'loss_spec', 'seed', 'years', 'method', 'native_budget', 'designer'}
    if not isinstance(request, dict) or set(request) != fields or request['schema'] != REQUEST_SCHEMA:
        raise ValueError('exact native-search-request.v15 fields required')
    designer = request['designer']
    if (not isinstance(designer, dict) or set(designer) != {'model', 'max_steps', 'max_tokens'}
            or designer['model'] != 'qwen3:8b'
            or type(designer['max_steps']) is not int or not 1 <= designer['max_steps'] <= 64
            or type(designer['max_tokens']) is not int or not 512 <= designer['max_tokens'] <= 8192):
        raise ValueError('fixed local model and bounded staged max_steps/max_tokens required')
    # Reuse the original SystemSpec/loss/seed/method/native-budget checks only.
    legacy = {**clone(request), 'schema': 'scienceutopia.native-search-request.v14',
        'designer': {'model': designer['model'], 'max_attempts': 1, 'max_tokens': designer['max_tokens']}}
    validate_legacy_request(legacy)
    if len(json.dumps(request, allow_nan=False).encode()) > 512_000:
        raise ValueError('search request exceeds byte budget')


def make_search_plan(request, *, source_commit, provider_binding):
    validate_search_request(request)
    validate_provider_binding(provider_binding)
    if not isinstance(source_commit, str) or not re.fullmatch('[a-f0-9]{40}', source_commit):
        raise ValueError('clean pinned source commit required')
    generations = request['native_budget'] if request['method'] == 'blackbox' else 2
    return {'schema': PLAN_SCHEMA, 'request': clone(request), 'request_sha256': digest(request),
        'source_commit': source_commit, 'provider_binding': clone(provider_binding),
        'stage_counts': [1] * request['native_budget'] if request['method'] == 'blackbox' else [2, 1, 1],
        'generator_calls': generations,
        'maximum_authoring_steps_per_generation': request['designer']['max_steps'],
        'maximum_designer_provider_attempts': generations * request['designer']['max_steps'],
        'authoring_protocol': 'staged-v15',
        'native_retry_policy': 'none; exact native checkpoint/response replay only',
        'failed_generation_policy': 'consume scheduled slots with null loss; no replacement',
        'objective_policy': 'declared LossSpec; technical validity separate; no merit/promotion veto',
        'origin': 'explicit-local-compute-consent', 'model_weights_trained': False}


class NativeStagedSearchController(NativeSearchController):
    plan_builder = staticmethod(make_search_plan)

    def projection(self, **kwargs):
        result = super().projection(**kwargs)
        result['schema'] = PROGRESS_SCHEMA
        result['authoring_protocol'] = 'staged-v15'
        result['maximum_designer_provider_attempts'] = self.plan['maximum_designer_provider_attempts']
        return result


class NativeStagedSearchQueue(NativeSearchQueue):
    search_protocol = 'staged-v15'
    plan_builder = staticmethod(make_search_plan)
    controller_type = NativeStagedSearchController
    database_name = 'native-search-jobs-v15.sqlite'

    def designer_provider_for(self, request):
        return clone(self.provider_binding)

    def get(self, identity):
        row, controller = self._load(identity)
        result = controller.projection(search_id=identity, status=row['status'],
            errors=[{'worker_error': row['error'], 'loss': None}] if row['error'] else [])
        result.update(created_at=row['created'], updated_at=row['updated'])
        from .native_staged_author_v15 import project_authoring_trace, protocol_binding
        records = controller.campaign.state['records'] + (
            [controller.campaign.state['pending']] if controller.campaign.state['pending'] else [])
        trace = project_authoring_trace(controller.directory / 'authoring',
            allowed_requests=[record['request'] for record in records],
            provider_binding=self.designer_provider_for(controller.request),
            settings={k: controller.request['designer'][k] for k in ('max_steps', 'max_tokens')},
            authoring_protocol=protocol_binding())
        result['authoring_trace'] = trace
        result['live_progress'] = super().live_progress(controller, observe_designer=False)
        generations = trace.get('generations', [])
        result['live_progress']['designer'] = {
            'generation_directories': len(generations),
            'attempts_started': sum(step['dispatch_intent'] for g in generations for step in g['steps']),
            'attempts_completed': sum(step['completed'] for g in generations for step in g['steps'])}
        result['live_progress']['warnings'].extend(trace.get('warnings', []))
        # Staged author receipts are distinct from legacy one-shot attempts.
        # Native physical costs/completion stay in independently audited records.
        return result

    def evidence(self, identity):
        return self.get(identity)
