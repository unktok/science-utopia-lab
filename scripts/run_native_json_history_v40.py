#!/usr/bin/env python3
"""Conditional prospective plain-JSON designer history; unchanged scientific pilot."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_native_designer_roles_v38 import (
    build_plan as previous_plan, execute as previous_execute, extra_arguments,
)
from scripts.run_native_staged_search_v15 import main as pilot_main
from utopia.optimization.native_designer_roles_v38 import make_search_plan
from utopia.optimization.native_designer_tools_v25 import PLAIN_JSON_HISTORY
from utopia.system.design_patch import digest

PROTOCOL = 'research/protocols/campaigns/native-json-history-v40-a1.md'


def build_plan(**kwargs):
    plan = previous_plan(**kwargs)
    for entry in plan['runs']:
        entry['request']['designer']['conversation_profile'] = PLAIN_JSON_HISTORY
        entry['runtime_plan'] = make_search_plan(entry['request'], source_commit=kwargs['source_commit'],
            provider_binding=kwargs['provider_binding'])
        entry['plan_sha256'] = digest(entry['runtime_plan'])
    plan.update(engineering_revision='v40-a1', protocol=PROTOCOL,
        conversation_profile=PLAIN_JSON_HISTORY)
    return plan


def execute(args):
    return previous_execute(args, plan_builder=build_plan, conversation_profile=PLAIN_JSON_HISTORY)


if __name__ == '__main__':
    raise SystemExit(pilot_main(execute_callback=execute, extra_arguments=extra_arguments))
