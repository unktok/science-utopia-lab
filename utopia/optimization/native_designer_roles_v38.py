"""Explicit local designer identity, separate from unchanged Qwen researchers.

Only operator-pinned, already installed local identities are supported. This
module adds no endpoint, remote provider, retry or scientific-policy template.
Legacy v14/v15 request/model guards remain unchanged.
"""
from __future__ import annotations

import json

from utopia.system.design_patch import clone, digest
from .native_search_v14 import validate_provider_binding
from .native_search_v15 import (
    NativeStagedSearchController, NativeStagedSearchQueue,
    make_search_plan as legacy_plan, validate_search_request as legacy_validate,
)
from .native_staged_author_v15 import LocalStagedQwenDesignerModel, StagedVocabularyGenerator
from .native_designer_tools_v25 import LEGACY_HISTORY, PLAIN_JSON_HISTORY, DIRECT_PROFILES, profile_options

REQUEST_SCHEMA = 'scienceutopia.native-search-request.v38'
PLAN_SCHEMA = 'scienceutopia.native-search-plan.v38'
PROGRESS_SCHEMA = 'scienceutopia.native-search-progress.v38'
LOCAL_DESIGNER_IDENTITIES = {
    'qwen3.6:35b-mlx-64k': 'f3ddc74319e42fad1cce455555e9f6864372665bcf9f0578b600f554787cbcc8',
}


def validate_designer_binding(binding, *, scientist_binding=None):
    """The corpus/image describe the common world, not a new researcher model."""
    if not isinstance(binding, dict):
        raise ValueError('explicit local designer provider required')
    name = binding.get('model')
    if (name not in LOCAL_DESIGNER_IDENTITIES
            or binding.get('model_digest') != LOCAL_DESIGNER_IDENTITIES[name]):
        raise ValueError('designer must match an explicitly approved installed local model/digest')
    # Reuse the unchanged native world binding validation, not its model choice.
    world = {**clone(binding), 'model': 'qwen3:8b'}
    validate_provider_binding(world)
    if scientist_binding is not None:
        validate_provider_binding(scientist_binding)
        if any(binding[key] != scientist_binding[key]
               for key in ('corpus_sha256', 'dataset_identity', 'corpus_years', 'image_id')):
            raise ValueError('designer and scientists must share the exact corpus/dataset/horizon/image')
    digest(binding)


def _legacy_validation_view(request):
    fields = {'schema', 'initial_system', 'loss_spec', 'seed', 'years', 'method', 'native_budget', 'designer'}
    if not isinstance(request, dict) or set(request) != fields or request.get('schema') != REQUEST_SCHEMA:
        raise ValueError('exact native-search-request.v38 fields required')
    designer = request['designer']
    if (not isinstance(designer, dict)
            or set(designer) - {'conversation_profile'} != {'model', 'max_steps', 'max_tokens', 'provider_binding'}
            or ('conversation_profile' in designer and designer['conversation_profile'] not in
                (PLAIN_JSON_HISTORY, *DIRECT_PROFILES))):
        raise ValueError('explicit separately bound designer and bounded steps/tokens required')
    validate_designer_binding(designer['provider_binding'])
    if designer['model'] != designer['provider_binding']['model']:
        raise ValueError('requested designer differs from its explicit provider binding')
    # Validation only: never persist/use this view as the actual request or
    # authoring provenance. Existing science/seed/loss/budget checks are reused.
    view = {**clone(request), 'schema': 'scienceutopia.native-search-request.v15',
            'designer': {'model': 'qwen3:8b', **{
                k: designer[k] for k in ('max_steps', 'max_tokens')}}}
    legacy_validate(view)
    if designer.get('conversation_profile') in DIRECT_PROFILES:
        from .native_designer_decoding_v24 import decoding_contract
        if designer['max_tokens'] != decoding_contract('staged-v15', conversation_profile=designer['conversation_profile'])['max_tokens']:
            raise ValueError('direct designer profile requires its exact source-owned decoding token budget')
    if len(json.dumps(request, allow_nan=False).encode()) > 512_000:
        raise ValueError('search request exceeds byte budget')
    return view


def validate_search_request(request):
    _legacy_validation_view(request)


def make_search_plan(request, *, source_commit, provider_binding):
    view = _legacy_validation_view(request)
    validate_designer_binding(request['designer']['provider_binding'], scientist_binding=provider_binding)
    plan = legacy_plan(view, source_commit=source_commit, provider_binding=provider_binding)
    plan.update(schema=PLAN_SCHEMA, request=clone(request), request_sha256=digest(request),
        designer_provider_binding=clone(request['designer']['provider_binding']),
        role_policy='scientist provider fixed; designer separately declared and source/model bound')
    plan.update(profile_options(request['designer'].get('conversation_profile', LEGACY_HISTORY)))
    if plan.get('conversation_profile') in DIRECT_PROFILES:
        from .native_designer_decoding_v24 import decoding_contracts
        plan['designer_decoding'] = decoding_contracts('staged-v15', conversation_profile=plan['conversation_profile'])
    return plan


class NativeRoleBoundSearchController(NativeStagedSearchController):
    plan_builder = staticmethod(make_search_plan)

    def projection(self, **kwargs):
        result = super().projection(**kwargs)
        result['schema'] = PROGRESS_SCHEMA
        result['role_bindings'] = {'scientist': clone(self.plan['provider_binding']),
                                  'designer': clone(self.plan['designer_provider_binding'])}
        return result


class NativeRoleBoundSearchQueue(NativeStagedSearchQueue):
    plan_builder = staticmethod(make_search_plan)
    controller_type = NativeRoleBoundSearchController
    database_name = 'native-search-jobs-v38.sqlite'

    def designer_provider_for(self, request):
        validate_designer_binding(request['designer']['provider_binding'], scientist_binding=self.provider_binding)
        return clone(request['designer']['provider_binding'])

    def run_one(self, factory_builder, *, generator_builder, source_commit, after_stage=None):
        def author(root, request, scientist_binding):
            if scientist_binding != self.provider_binding:
                raise ValueError('worker scientist provider changed')
            return generator_builder(root, request, self.designer_provider_for(request))
        return super().run_one(factory_builder, generator_builder=author,
            source_commit=source_commit, after_stage=after_stage)


class LocalRoleBoundDesignerModel(LocalStagedQwenDesignerModel):
    """Unchanged literal staged transport, explicitly different local weights."""
    def __init__(self, *args, readiness_scope='literal-controls-v16', **kwargs):
        self.readiness_scope = readiness_scope
        super().__init__(*args, **kwargs)

    def _validate_model_binding(self):
        validate_designer_binding(self.binding)

    def _check_preflight(self, protocol):
        if self.preflight_certificate is not None:
            from .native_designer_preflight import require_certificate
            return require_certificate(self.preflight_certificate, self.binding,
                protocol=protocol, session=self.session, scope=self.readiness_scope,
                **profile_options(self.conversation_profile))
        return None


def staged_model_type(provider):
    # The old class is retained verbatim for old callers and monkeypatched
    # calibrations. A different model never falls back to Qwen3-8B.
    if isinstance(provider, dict) and provider.get('model') == 'qwen3:8b':
        return LocalStagedQwenDesignerModel
    validate_designer_binding(provider)
    return LocalRoleBoundDesignerModel


def make_local_role_bound_generator(directory, *, image_id, provider_binding,
                                    max_steps, max_tokens, inference_lock=None,
                                    preflight_certificate=None, readiness_scope='literal-controls-v16',
                                    conversation_profile=LEGACY_HISTORY):
    from .native_designer_preflight import require_certificate
    validate_designer_binding(provider_binding)
    profile = profile_options(conversation_profile)
    require_certificate(preflight_certificate, provider_binding, protocol='staged-v15', scope=readiness_scope,
        **profile)
    return StagedVocabularyGenerator(LocalRoleBoundDesignerModel(provider_binding,
        inference_lock=inference_lock, preflight_certificate=preflight_certificate,
        readiness_scope=readiness_scope, **profile),
        directory, image_id=image_id, provider_binding=provider_binding,
        max_steps=max_steps, max_tokens=max_tokens, **profile)
