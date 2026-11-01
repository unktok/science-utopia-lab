from copy import deepcopy
import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.optimization.test_native_free_source import recorded_selection
from utopia.optimization.native_region_design import compile_region, probe_selection_region
from utopia.system.native_kernel import WORLD_ARTIFACT, CONTROL_ARTIFACT
from utopia.system.design_patch import apply_design_patch


def port(name, channel, kind):
    return {'port_id': name, 'channel': channel, 'artifact_type': kind, 'required': True}


def fixture_manifest():
    # Explicit developer-written QA manifest, NOT a model invention result.
    producer = """def step(context):
    world = context['inputs']['evidence'][0]['payload']
    items = []
    for c in world['conferences']['conferences']:
        for p in c['submitted_papers']:
            reviews = c['reviews'].get(p['id'], [])
            items.append({'paper_id': p['id'], 'conference_id': c['conference_id'],
                'score': sum(r['overall_score'] for r in reviews) / len(reviews) if reviews else 0.0})
    return {'outputs': {'packets': [{'payload': {'candidates': items}}]},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    consumer = """def step(context):
    items = context['inputs']['dossier'][0]['payload']['candidates']
    values = [{'payload': {'paper_id': p['paper_id'], 'conference_id': p['conference_id'],
        'final_score': p['score'], 'decision': 'accept'}} for p in items]
    if not values:
        values = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'ready': [{'payload': {'year': context['period']}}], 'verdicts': values},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    protocol = 'qa-arbitrary-dossier-format'
    def node(name, phase, inputs, outputs, source):
        return {'mechanism_id': name, 'family': 'custom', 'phase': phase, 'inputs': inputs, 'outputs': outputs,
            'parameters': {}, 'algorithm_name': 'Explicit QA-only institution', 'python_code': source,
            'input_schemas': {p['port_id']: {'type': 'object'} for p in inputs},
            'output_schemas': {p['port_id']: {'type': 'object'} for p in outputs}, 'state_schema': {'type': 'object'}}
    nodes = [node('qa-evidence-commons', 129, [port('evidence', 'artifact', WORLD_ARTIFACT)], [port('packets', 'artifact', protocol)], producer),
        node('qa-decision-assembly', 147, [port('trigger', 'signal', CONTROL_ARTIFACT), port('dossier', 'artifact', protocol)],
            [port('ready', 'signal', CONTROL_ARTIFACT), port('verdicts', 'decision', 'native-paper-decision')], consumer)]
    def edge(a, p, b, q, channel):
        return {'source_mechanism': a, 'source_port': p, 'target_mechanism': b, 'target_port': q, 'channel': channel, 'latency': 0}
    edges = [edge('world.review', 'world', 'qa-evidence-commons', 'evidence', 'artifact'),
        edge('world.review', 'next', 'qa-decision-assembly', 'trigger', 'signal'),
        edge('qa-evidence-commons', 'packets', 'qa-decision-assembly', 'dossier', 'artifact'),
        edge('qa-decision-assembly', 'ready', 'world.publication', 'after', 'signal'),
        edge('qa-decision-assembly', 'verdicts', 'world.publication', 'decisions', 'decision')]
    return {'rationale': 'QA free-source/protocol/wiring compiler, not an empirical invention claim', 'nodes': nodes, 'connections': edges}


def test_joint_arbitrary_protocol_nodes_and_wiring_probe_then_original_world(recorded_selection):
    campaign, factory, executor, provider = recorded_selection
    manifest = fixture_manifest()
    patch, child = compile_region(campaign.initial, manifest, removed_nodes=['world.selection'], image_id=executor.image_id)
    assert apply_design_patch(campaign.initial, patch) == child
    assert 'world.selection' not in {n.mechanism_id for n in child.mechanisms}
    rows = provider('world.selection', campaign.initial, campaign.state['records'])
    probe = probe_selection_region(campaign.initial, child, rows, executor=executor)
    assert len(probe['runs']) == 6 and all(len(r['code_executions']) == 2 for r in probe['runs'])
    assert any(r['decisions_changed'] for r in probe['runs'])
    second = campaign.advance(simulation_factory=factory, proposer=lambda *a: patch)
    assert second['observation']['status'] == 'complete'
    assert second['observation']['loss'] < campaign.state['records'][0]['observation']['loss']


def test_new_region_cannot_mutate_unrelated_native_boundary(recorded_selection):
    campaign, _, executor, _ = recorded_selection
    manifest = fixture_manifest()
    manifest['connections'][-1]['target_mechanism'] = 'world.funding'
    with pytest.raises(ValueError, match='outside the declared native boundary'):
        compile_region(campaign.initial, manifest, removed_nodes=['world.selection'], image_id=executor.image_id)


def test_real_native_identity_checks_do_not_accept_invented_papers(recorded_selection):
    campaign, _, executor, provider = recorded_selection
    manifest = fixture_manifest()
    manifest['nodes'][1]['python_code'] = manifest['nodes'][1]['python_code'].replace("'paper_id': p['paper_id']", "'paper_id': p['paper_id'] + '-invented'")
    _, child = compile_region(campaign.initial, manifest, removed_nodes=['world.selection'], image_id=executor.image_id)
    rows = provider('world.selection', campaign.initial, campaign.state['records'])
    with pytest.raises(ValueError, match='real native paper'):
        probe_selection_region(campaign.initial, child, rows, executor=executor)
