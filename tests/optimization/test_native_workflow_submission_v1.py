from dataclasses import replace
import json

import pytest
from jsonschema import ValidationError

from tests.optimization.test_native_workflow_domain_v4 import IMAGE
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, GeneratedMixedDesign
from utopia.optimization.native_workflow_domain_v4 import workflow_design_space, post_funding_cost_control
from utopia.optimization.native_workflow_submission_v1 import (
    workflow_context, compile_submission, control_submission, graph_projection)
from utopia.system import ConnectionSpec, ChannelKind, SystemSpec
from utopia.system.design_patch import clone
from utopia.system.native_planning_controls import planning_controls


def request(directory):
    anchor = planning_controls(IMAGE, seed=61001)['assignment-reserve21-no-review-all']
    c = NativeAdaptiveDesignCampaign(directory, initial_system=anchor, loss_spec=loss_spec(), seeds=[61001],
        world_binding={'source_commit': 'a' * 40, 'model_digest': 'b' * 64, 'corpus_sha256': 'c' * 64},
        strategies={'scripted': {'kind': 'SCRIPTED-unit'}}, mode='blackbox', seed=68011,
        design_space=workflow_design_space(anchor))
    return c._request([], c._validate(), 1)


def contrast_submission(req):
    parent = SystemSpec.from_dict(req['parent_system']); changed = post_funding_cost_control(parent)
    original_phases = {s.mechanism_id: s.phase for s in parent.schedules}
    return {'phase_updates': {s.mechanism_id: s.phase for s in changed.schedules
            if s.phase != original_phases[s.mechanism_id]},
        'remove_connections': [i for i, e in enumerate(parent.connections) if e not in changed.connections],
        'add_connections': [e for e in changed.to_dict()['connections'] if e not in parent.to_dict()['connections']],
        'rationale': 'SCRIPTED hand timing contrast; not an optimizing inventor'}


def test_identity_and_graph_edits_compile_into_existing_generated_design(tmp_path):
    req = request(tmp_path / 'c'); parent = SystemSpec.from_dict(req['parent_system'])
    control = compile_submission(req, control_submission(req))
    assert control['base_patch'] is None and control['provenance']['retained_parent_explicitly']
    submission = contrast_submission(req)
    definition = compile_submission(req, submission)
    mixed = GeneratedMixedDesign(parent, definition, loss_spec=req['loss_spec'], seed=42, single_draw_blackbox=True)
    assert mixed.base.mechanisms == parent.mechanisms
    assert mixed.base.metadata == parent.metadata and mixed.base.initial_state == parent.initial_state
    assert sum(a != b for a, b in zip(parent.schedules, mixed.base.schedules)) == 3
    assert len(set(mixed.base.connections) - set(parent.connections)) == 5
    assert definition['provenance']['raw_values_changed_by_host'] is False


@pytest.mark.parametrize('bad', ['bool-phase', 'float-phase', 'bool-index', 'float-index', 'bool-latency',
    'negative-phase', 'duplicate-index', 'unknown-index', 'unknown-node', 'unknown-port', 'wrong-type',
    'backward', 'extra-field', 'missing-field', 'source-edit', 'blank-rationale'])
def test_untrusted_operations_are_rejected_without_host_coercion_or_repair(tmp_path, bad):
    req = request(tmp_path / 'c'); s = control_submission(req)
    if bad == 'bool-phase': s['phase_updates']['world.open'] = False
    elif bad == 'float-phase': s['phase_updates']['world.open'] = 0.0
    elif bad == 'bool-index': s['remove_connections'] = [True]
    elif bad == 'float-index': s['remove_connections'] = [0.0]
    elif bad == 'bool-latency': s['add_connections'][0]['latency'] = False
    elif bad == 'negative-phase': s['phase_updates']['world.open'] = -1
    elif bad == 'duplicate-index': s['remove_connections'] *= 2
    elif bad == 'unknown-index': s['remove_connections'] = [9999]
    elif bad == 'unknown-node': s['phase_updates'] = {'not-a-node': 2}
    elif bad == 'unknown-port': s['add_connections'][0]['source_port'] = 'not-a-port'
    elif bad == 'wrong-type': s['add_connections'][0]['channel'] = 'resource'
    elif bad == 'backward': s['phase_updates'] = {'world.costs': 200}
    elif bad == 'extra-field': s['add_connections'][0]['prose'] = 'Host should fix this'
    elif bad == 'missing-field': s.pop('remove_connections')
    elif bad == 'source-edit': s['source'] = 'def step(context): return {}'
    else: s['rationale'] = '  '
    with pytest.raises((ValueError, ValidationError)):
        compile_submission(req, s)


def test_source_once_history_graphs_loss_and_nulls_are_literal_and_reconstructable(tmp_path):
    req = request(tmp_path / 'c'); anchor = SystemSpec.from_dict(req['parent_system'])
    changed = post_funding_cost_control(anchor)
    reordered = replace(changed, connections=tuple(reversed(changed.connections)))
    for spec in (anchor, changed, reordered):
        projection = graph_projection(anchor, spec)
        edges = []
        for e in projection['ordered_connections']:
            if 'anchor_index' in e: edges.append(anchor.connections[e['anchor_index']])
            else: edges.append(ConnectionSpec(**{**e['literal'], 'channel': ChannelKind(e['literal']['channel'])}))
        rebuilt = replace(anchor, connections=tuple(edges), schedules=tuple(replace(s,
            phase=projection['phase_updates_from_anchor'].get(s.mechanism_id, s.phase)) for s in anchor.schedules))
        assert rebuilt.to_dict() == spec.to_dict()
    req['observations'] = [{'suggestion': {'candidate': s.to_dict()}, 'observation': {
        'observation_id': 'SCRIPTED-' + str(i), 'status': 'complete' if i else 'failed', 'loss': -i if i else None,
        'metadata': {'measurements': [{'metrics': {'probe': {'value': i}}}] if i else [],
            'technical_failures': [] if i else [{'error': 'SCRIPTED recorded failure'}]}}}
        for i, s in enumerate((anchor, changed, changed, reordered))]
    req['history'] = [{'request_sha256': 'a' * 64, 'generation_error': {'message': 'SCRIPTED invalid grammar'},
        'definition': {'workflow_submission_failure': {'literal_submission': {'x': [None, True]},
            'error': {'message': 'SCRIPTED source error'}}}}]
    context = workflow_context(req)
    assert len(context['observations']) == 4 and len(context['observed_graphs']) == 3
    assert [r['loss'] for r in context['observations']] == [None, -1, -2, -3]
    assert context['consumed_generation_nulls'][0]['literal_submission_failure']['literal_submission'] == {'x': [None, True]}
    assert context['fixed_mechanisms'] == anchor.to_dict()['mechanisms']
    assert 'candidate' not in json.dumps(context['observations'])
