"""Finite same-authority original-topic control study, not optimization."""
import argparse
from pathlib import Path

from scripts import run_native_legacy_choice_pilot_v1 as base
from utopia.optimization.native_designer_preflight import runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_resource_cost import (
    CONTRACT as COST_CONTRACT, METRIC, UNCOLLECTED_METRIC, measure, measure_from_checkpoints)
from utopia.optimization.native_workflow_domain_v5 import (
    legacy_topic_workflow_design_space, require_legacy_topic_workflow_candidate,
    verify_legacy_topic_workflow_interval)
from utopia.system import SystemSpec
from utopia.system.design_patch import clone
from utopia.system.native_legacy_topic_controls import legacy_topic_control
from utopia.utils.data_utils import file_sha256

ROOT = base.ROOT
SCHEMA = 'scienceutopia.native-legacy-topic-pilot.v1'
PROTOCOL = 'research/protocols/campaigns/native-legacy-topic-feasibility-v1.md'
ROLE = 'developer-same-authority-topic-control'
SEED = 61001
LABELS = ('core-only', 'core-plus-related')
ADAPTER_SOURCE = 'ccf8fe393fec32ad1c2ab9d77930c7786c03b226'
ADAPTERS = {
    'utopia/system/native_open_domain.py': 'Register explicit legacy-topic action; existing native effects unchanged',
    'utopia/optimization/native_fixed_production_domain.py': 'Old domains reject new action grants',
    'utopia/optimization/native_workflow_domain_v4.py': 'Shared unchanged witness core; old v4 rejects new action grants',
}
read, save, utc = base.read, base.save, base.utc


def native_sources(original, *, source_root=None):
    return base.workflow.native_sources(original, adapters={
        path: {'source_commit': ADAPTER_SOURCE, 'role': role} for path, role in ADAPTERS.items()},
        source_root=source_root)


def build_plan(original, audit, fixed, *, source, origin, observer_backend, original_sources):
    p = base.build_plan(original, audit, fixed, source=source, origin=origin,
        observer_backend=observer_backend, original_sources=original_sources)
    anchor = SystemSpec.from_dict(original['reference_systems']['post-funding-cost'])
    systems = {label: legacy_topic_control(anchor, candidate_policy=label) for label in LABELS}
    for spec in systems.values():
        require_legacy_topic_workflow_candidate(SystemSpec.from_dict(p['initial_system']), spec)
    p.update(schema=SCHEMA + '.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT / PROTOCOL),
        experiment={'protocol': PROTOCOL, 'role': ROLE},
        design_space=legacy_topic_workflow_design_space(SystemSpec.from_dict(p['initial_system'])),
        additional_measurements={'contract': clone(COST_CONTRACT), 'metrics': [METRIC, UNCOLLECTED_METRIC],
            'source_file': 'utopia/optimization/native_resource_cost.py',
            'source_sha256': file_sha256(ROOT / 'utopia/optimization/native_resource_cost.py'),
            'optimization_loss_changed': False},
        jobs=[{'identity': 'legacy-topic-' + label, 'condition': label, 'seed': SEED,
               'system': systems[label].to_dict()} for label in LABELS])
    p['world'].update(experiment=clone(p['experiment']), classification='actual-native-legacy-topic-pilot-v1')
    p['budget']['native_worlds_upper_bound'] = 2
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean legacy-topic pilot source/runtime required')
    original, audit, fixed = base.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, fixed, source=p['source_commit'], origin=p['origin'],
        observer_backend=p['observer_contract']['backend'], original_sources=native_sources(original['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal same-authority control/world/metric/budget reconstruction differs')
    return p


def interval(plan, system, events, seed):
    if seed != SEED:
        raise ValueError('explicit reused development seed required')
    return verify_legacy_topic_workflow_interval(SystemSpec.from_dict(plan['initial_system']), system, events, years=4)


def additional_from_checkpoints(base_measurement, cell):
    paths = []
    for year in range(5):
        matches = list(cell.rglob(f'portable_checkpoint_year_{year}.json.gz'))
        if len(matches) != 1:
            raise ValueError('unique original full annual checkpoint path required')
        paths.append(matches[0])
    return measure_from_checkpoints(base_measurement, paths)


def observe(root, p, job, observer):
    return base.observe(root, p, job, observer, role=ROLE, interval_reader=interval, metric_adapter=measure)


def run(root):
    return base.run(root, plan_reader=require_plan, observe_function=observe, schema=SCHEMA)


def prepare(args):
    return base.prepare(args, plan_builder=build_plan, plan_reader=require_plan, source_reader=native_sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run', 'origin-source', 'audit-one', 'audit-two'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args, key) is None for key in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('closed original run/source and both audits required')
        prepare(args)
    else:
        run(args.output)


if __name__ == '__main__':
    main()
