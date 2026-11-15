"""Two prospective native opportunity controls, not automatic invention.

Only institution source changes. Original researcher, ledger and cost consumers
remain unchanged; unpaid cost and attrition are reported, not vetoed.
"""
import argparse
from pathlib import Path

from scripts import run_native_legacy_topic_pilot_v1 as topic
from scripts import run_native_topic_free_optimization_v1 as free
from utopia.optimization.native_designer_preflight import runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_resource_cost import measure
from utopia.optimization.native_topic_objectives_v1 import objective_specs, OBJECTIVES
from utopia.optimization.native_workflow_domain_v5 import (
    require_legacy_topic_workflow_candidate, verify_legacy_topic_workflow_interval)
from utopia.system import SystemSpec
from utopia.system.native_terminal_cost_controls_v1 import terminal_consolidation_control
from utopia.utils.data_utils import file_sha256

ROOT = topic.ROOT
SCHEMA = 'scienceutopia.native-terminal-cost-pilot.v1'
PROTOCOL = 'research/protocols/campaigns/native-terminal-cost-opportunity-v1.md'
ROLE = 'developer-terminal-collected-cost-control'
SEED = 61001
LABELS = ('strong-related-reference', 'terminal-consolidation')
read, save, utc = topic.read, topic.save, topic.utc
additional_from_checkpoints = topic.additional_from_checkpoints


def native_sources(original):
    # Exact versioned adapters already present in the original-topic free study;
    # original scientist/effect files outside them remain byte-identical.
    return free.native_sources(original, pinned_revision(ROOT))


def build_plan(original, audit, fixed, *, source, origin, observer_backend, original_sources):
    p = topic.build_plan(original, audit, fixed, source=source, origin=origin,
        observer_backend=observer_backend, original_sources=original_sources)
    parent = SystemSpec.from_dict(p['jobs'][1]['system'])
    systems = (parent, terminal_consolidation_control(parent, terminal_year=4))
    for spec in systems:
        require_legacy_topic_workflow_candidate(SystemSpec.from_dict(p['initial_system']), spec)
    p.update(schema=SCHEMA + '.plan', protocol=PROTOCOL,
        protocol_sha256=file_sha256(ROOT / PROTOCOL),
        experiment={'protocol': PROTOCOL, 'role': ROLE},
        losses=objective_specs(original['losses']), objectives=list(OBJECTIVES),
        objective_comparison={'target': OBJECTIVES[-1], 'optimization_study': False,
            'same_predeclared_coefficient': 0.1, 'historical_losses_or_selection_changed': False,
            'hypothesis_is_development_informed': True, 'automatic_invention': False,
            'unpaid_cost_or_attrition_veto': False},
        jobs=[{'identity': 'terminal-cost-' + label, 'condition': label, 'seed': SEED,
               'system': spec.to_dict()} for label, spec in zip(LABELS, systems)])
    p['world'].update(experiment=p['experiment'].copy(), classification='actual-native-terminal-cost-pilot-v1')
    p['additional_measurements'].update(
        prospective_comparison_loss_id=p['losses'][OBJECTIVES[-1]]['id'],
        optimization_study=False, historical_losses_unchanged=True)
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean terminal-cost source/runtime required')
    original, audit, fixed = topic.base.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, fixed, source=p['source_commit'], origin=p['origin'],
        observer_backend=p['observer_contract']['backend'], original_sources=native_sources(original['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal terminal-cost systems/objectives/budgets reconstruction differs')
    return p


def interval(plan, system, events, seed):
    if seed != SEED:
        raise ValueError('explicit reused development seed required')
    return verify_legacy_topic_workflow_interval(SystemSpec.from_dict(plan['initial_system']), system, events, years=4)


def observe(root, plan, job, observer):
    return topic.base.observe(root, plan, job, observer, role=ROLE,
        interval_reader=interval, metric_adapter=measure)


def prepare(args):
    return topic.base.prepare(args, plan_builder=build_plan, plan_reader=require_plan, source_reader=native_sources)


def run(root):
    return topic.base.run(root, plan_reader=require_plan, observe_function=observe, schema=SCHEMA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run', 'origin-source', 'audit-one', 'audit-two'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args, key) is None for key in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('closed original run/source and matching audits required')
        prepare(args)
    else:
        run(args.output)


if __name__ == '__main__':
    main()
