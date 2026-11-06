#!/usr/bin/env python3
"""Explicit finite authoring recovery over the unchanged original researcher world."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_native_designer_roles_v38 import build_plan as previous_plan, execute as previous_execute, extra_arguments
from scripts.run_native_staged_search_v15 import main as pilot_main
from utopia.optimization.native_authoring_recovery_v44 import MAX_STEPS, SUBMISSION_RESERVE
from utopia.optimization.native_designer_tools_v25 import AUTHORING_RECOVERY
from utopia.optimization.native_designer_roles_v38 import make_search_plan
from utopia.optimization.native_designer_decoding_v24 import decoding_contracts
from utopia.system.design_patch import digest

PROTOCOL = 'research/protocols/campaigns/native-authoring-recovery-v44-a1.md'


def build_plan(**kwargs):
    plan = previous_plan(**kwargs)
    for entry in plan['runs']:
        entry['request']['designer'].update(conversation_profile=AUTHORING_RECOVERY, max_steps=MAX_STEPS)
        entry['runtime_plan'] = make_search_plan(entry['request'], source_commit=kwargs['source_commit'],
            provider_binding=kwargs['provider_binding'])
        entry['plan_sha256'] = digest(entry['runtime_plan'])
    # Verify the previously unimplemented arm first, rather than waiting for
    # four more already-understood throughput worlds before observing it.
    plan['runs'].sort(key=lambda entry: entry['id'] != 'efficiency')
    plan.update(engineering_revision='v44-a1', protocol=PROTOCOL, conversation_profile=AUTHORING_RECOVERY,
        designer_decoding=decoding_contracts('staged-v15', conversation_profile=AUTHORING_RECOVERY),
        authoring_workflow={'maximum_steps': MAX_STEPS, 'submission_reserve': SUBMISSION_RESERVE,
            'implementation_checkpoint_after_inspections': 3,
            'no_required_submission_explanation': True, 'all_calls_charged': True},
        native_campaign_status='User-authorized finite repair verification and actual institutional search')
    plan['budget'].update(per_generation_tool_steps=MAX_STEPS,
        maximum_generation_POSTs=plan['budget']['free_generations'] * MAX_STEPS,
        maximum_designer_digest_preflight_GETs=plan['budget']['free_generations'] * MAX_STEPS)
    return plan


def execute(args):
    return previous_execute(args, plan_builder=build_plan, conversation_profile=AUTHORING_RECOVERY)


if __name__ == '__main__':
    raise SystemExit(pilot_main(execute_callback=execute, extra_arguments=extra_arguments))
