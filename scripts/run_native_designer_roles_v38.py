#!/usr/bin/env python3
"""Explicit designer-only local-model change; Qwen3-8B scientists stay fixed."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_native_staged_search_v15 import build_plan as old_pilot_plan
from scripts.run_native_staged_search_v15 import execute as execute_pilot, main as pilot_main
from utopia.optimization.native_designer_roles_v38 import (
    NativeRoleBoundSearchQueue, make_search_plan, make_local_role_bound_generator,
    validate_designer_binding,
)
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.role-bound-native-search-pilot.v38'
CLASSIFICATION = 'actual-local-separate-designer-fixed-qwen-researchers-v38'
ENGINEERING_REVISION = 'v39-a1'
PROTOCOL = 'research/protocols/campaigns/native-execution-readiness-v39-a1.md'
READINESS_SCOPE = 'execution-readiness-v39'


def build_plan(*, source_commit, initial_system, provider_binding,
               runtime_seed_binding, designer_provider_binding):
    validate_designer_binding(designer_provider_binding, scientist_binding=provider_binding)
    plan = old_pilot_plan(source_commit=source_commit, initial_system=initial_system,
        provider_binding=provider_binding, runtime_seed_binding=runtime_seed_binding)
    for entry in plan['runs']:
        request = entry['request']
        request['schema'] = 'scienceutopia.native-search-request.v38'
        request['designer'].update(model=designer_provider_binding['model'],
            provider_binding=clone(designer_provider_binding))
        entry['runtime_plan'] = make_search_plan(request, source_commit=source_commit,
            provider_binding=provider_binding)
        entry['plan_sha256'] = digest(entry['runtime_plan'])
    plan.update(schema=SCHEMA, classification=CLASSIFICATION,
        engineering_revision=ENGINEERING_REVISION, protocol=PROTOCOL,
        readiness_scope=READINESS_SCOPE,
        designer_provider_binding=clone(designer_provider_binding),
        authoring='separately pinned local LLM designer only; no human/Codex candidate implementation',
        role_policy='Qwen3-8B researchers unchanged; only the local designer differs',
        loaded_context_policy='sequential designer40960 then explicit empty-prompt scientist40960 load before launch; explicit scientist40960 load/check before each world; no global backend change',
        native_campaign_status='authorized finite eight-slot development pilot; no failed-slot replenishment')
    plan['budget']['maximum_added_loaded_context_GETs_without_resume'] = 10
    plan['budget']['maximum_explicit_empty_prompt_scientist_load_POSTs_without_resume'] = 9
    plan['budget']['maximum_explicit_empty_prompt_designer_load_POSTs_without_resume'] = 1
    return plan


def execute(args):
    config = json.loads(args.designer_provider_config.read_text())
    if not isinstance(config, dict) or set(config) != {'provider_binding'}:
        raise ValueError('exact operator-owned designer provider configuration required')
    from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
    def factory(*a, **kw):
        return LocalRoleBoundNativeFactory(*a, designer_provider=config['provider_binding'], **kw)
    def generator(*a, **kw):
        return make_local_role_bound_generator(*a, readiness_scope=READINESS_SCOPE, **kw)
    return execute_pilot(args, plan_builder=build_plan, queue_type=NativeRoleBoundSearchQueue,
        designer_provider=config['provider_binding'], generator_factory=generator,
        native_factory_type=factory, readiness_scope=READINESS_SCOPE)


def extra_arguments(parser):
    parser.add_argument('--designer-provider-config', type=Path, required=True,
        help='operator-owned separately pinned local designer binding; no remote URL or credentials')


if __name__ == '__main__':
    raise SystemExit(pilot_main(execute_callback=execute, extra_arguments=extra_arguments))
