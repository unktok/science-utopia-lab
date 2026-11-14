"""Static timing corners for prospective mechanism identification, not a study.

These are developer controls, never optimizer inventions or replacements for
failed submissions. Only exact existing phases/connections change. No native
world, designer, component code, metric, objective or evaluation seed executes.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from scripts.reports.native_workflow_objective_loop_v1 import graph_change
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_workflow_domain_v4 import edit_workflow, post_funding_cost_control
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-workflow-timing-corners.v1'
LEVELS = ((False, False), (True, False), (False, True), (True, True))


def corner(anchor, *, late_liquidity, late_cost):
    if type(late_liquidity) is not bool or type(late_cost) is not bool:
        raise ValueError('two explicit boolean timing factors required')
    phases = {s.mechanism_id: s.phase for s in anchor.schedules}
    grant = phases['world.funding']
    if (not phases['world.submission'] < phases['developer-liquidity-director']
            < phases['developer-liquidity-effects'] < phases['world.costs'] < grant
            or phases['world.communication'] <= grant + 3):
        raise ValueError('exact early liquidity/cost anchor and three free post-funding phases required')
    updates = {}; changes = []
    if late_cost:
        updates['world.costs'] = grant + 3
        changes.extend((
            ('world.submission', 'next', 'world.costs', 'after', 'world.funding'),
            ('world.costs', 'next', 'world.selection', 'after', 'world.submission'),
            ('world.funding', 'next', 'world.communication', 'after', 'world.costs'),
            ('world.costs', 'world', 'native-feature-extractor', 'observations', 'world.submission')))
    if late_liquidity:
        updates.update({'developer-liquidity-director': grant + 1, 'developer-liquidity-effects': grant + 2})
        changes.append(('world.submission', 'world', 'developer-liquidity-director', 'world', 'world.funding'))
    rewires = []
    for source, port, target, target_port, replacement in changes:
        found = [e for e in anchor.connections if (e.source_mechanism, e.source_port,
            e.target_mechanism, e.target_port, e.latency) == (source, port, target, target_port, 0)]
        if len(found) != 1:
            raise ValueError('one exact declared anchor edge required for a timing contrast')
        rewires.append((found[0], replace(found[0], source_mechanism=replacement)))
    return edit_workflow(anchor, phase_updates=updates, rewires=rewires)


def describe(anchor):
    rows = []
    for liquidity, cost in LEVELS:
        spec = corner(anchor, late_liquidity=liquidity, late_cost=cost)
        rows.append({'label': ('late' if liquidity else 'early') + '-liquidity_' + ('late' if cost else 'early') + '-cost',
            'late_liquidity': liquidity, 'late_cost': cost, 'system': spec.to_dict(),
            'graph_from_anchor': graph_change(anchor.to_dict(), spec.to_dict()),
            'liquidity_snapshot_source': 'world.funding' if liquidity else 'world.submission',
            'selection_feature_snapshot_source': 'world.submission' if cost else 'world.costs'})
    if (rows[0]['system'] != anchor.to_dict()
            or rows[3]['system'] != post_funding_cost_control(anchor).to_dict()
            or len({digest(r['system']) for r in rows}) != 4):
        raise ValueError('four unique corners must retain exact original and joint hand-control endpoints')
    return rows


def export(args):
    path, out = args.anchor_plan.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(path.parent):
        raise ValueError('fresh static output outside the original raw directory required')
    source = pinned_revision(ROOT); before = file_sha256(path)
    p = checked(json.loads(path.read_text()))
    if p['schema'] != 'scienceutopia.native-workflow-objective-loop.v1.plan':
        raise ValueError('explicit workflow plan anchor required, not an arbitrary inferred baseline')
    rows = describe(SystemSpec.from_dict(p['initial_system']))
    report = {'schema': SCHEMA, 'analysis_source_commit': source,
        'anchor_plan_sha256': p['content_sha256'], 'anchor_plan_file_sha256': before,
        'anchor_source_commit': p['source_commit'], 'corners': rows,
        'interpretation': {
            'hand_designed_controls': True, 'automatically_invented': False,
            'sources_parameters_native_effects_initial_state_changed': False,
            'graph_validation_is_execution_evidence': False,
            'isolated_cost_order_effect_identified': False,
            'timing_levels_hold_information_fixed': False,
            'information_caveat': 'Late cost requires the declared pre-cost submission snapshot for selection features; '
                'late liquidity reads the declared post-funding snapshot. Freshness and source are part of each '
                'intervention. Four legal graphs alone do not identify a pure action-timing or information effect.',
            'source_plan_normal_closure_required_or_claimed': False,
            'new_scientific_comparison_queued': False, 'new_native_worlds': 0,
            'new_model_calls': 0, 'new_component_code_executions': 0,
            'loss_selection_or_failed_submission_changed': False, 'publication_ready': False}}
    if file_sha256(path) != before or pinned_revision(ROOT) != source:
        raise ValueError('static anchor or reader source changed')
    out.mkdir(parents=True); save(out / 'report.json', report)
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': {str(path): before},
        'analysis_source_commit': source, 'report_file_sha256': file_sha256(out / 'report.json'),
        'new_model_calls': 0, 'new_native_worlds': 0})
    print(json.dumps({'corners': len(rows), 'new_native_worlds': 0, 'new_model_calls': 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anchor-plan', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
