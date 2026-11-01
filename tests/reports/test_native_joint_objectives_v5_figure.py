"""All synthetic figure output stays in temporary, explicitly labelled paths."""
from copy import deepcopy
import json

import pytest

from scripts.figures.native_joint_objectives_v5 import FIXTURE, ROOT, _draw_graph, _node_label, graph_cut, load_evidence, make_figure
from tests.optimization.test_native_region_design import fixture_manifest
from utopia.optimization.native_region_design import compile_region
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


def report_fixture():
    image = 'sha256:' + 'a' * 64
    parent = selection_source_slot(legacy_world_system(), image_id=image)
    _, child = compile_region(parent, fixture_manifest(), removed_nodes=['world.selection'], image_id=image)
    report = {'schema': 'scienceutopia.native-joint-objectives-analysis.v5', 'classification': FIXTURE,
        'status': 'declared-budget-complete', 'arms': {}}
    for filename, path, selected in [('native-joint-v5-throughput.json', [-1, -3], 1),
                                      ('native-joint-v5-net-reviewed-utility.json', [.5, .7], 0)]:
        loss = json.loads((ROOT / 'research/objectives/losses' / filename).read_text())
        rows = [{'loss': value, 'status': 'complete', 'system_fingerprint': spec.fingerprint,
            'difference': {'candidate_fingerprint': spec.fingerprint}, 'measurements': [], 'cross_objective': {}}
            for value, spec in zip(path, (parent, child))]
        system = (parent, child)[selected]
        report['arms'][loss['id']] = {'loss_spec': loss, 'audit': {'rows': rows, 'loss_path': path},
            'loss_path': path, 'selected_index': selected, 'selected_system': system.to_dict(),
            'selected_fingerprint': system.fingerprint, 'authoring_error': None}
    return report


def terminal_failure_fixture():
    report = report_fixture()
    parent = report['arms']['native-joint-v5-net-reviewed-utility']
    system, fingerprint = deepcopy(parent['selected_system']), parent['selected_fingerprint']
    for arm in report['arms'].values():
        arm.update(selected_system=system, selected_fingerprint=fingerprint, selected_index=0,
            authoring_error={'proposal_index': 1, 'loss': None, 'error': 'bounded technical drafts failed'})
        arm['audit']['rows'] = arm['audit']['rows'][:1]
        arm['loss_path'] = arm['loss_path'][:1]
        arm['audit']['loss_path'] = arm['loss_path']
    report['status'] = 'terminal-with-preserved-failures'
    return report


def test_native_display_labels_do_not_replace_authoritative_graph_ids():
    assert _node_label('world.review', native=True) == 'review'
    assert _node_label('world.publication', native=True) == 'publication'
    assert _node_label('generated-123456789abc.world.review', native=False) == 'world.review'
    report = terminal_failure_fixture()
    assert load_evidence(report)[0]['cut']['incoming_nodes'] == ['world.review']


def test_port_key_separated_from_failure_note_and_terminal_fixture_render(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    report = terminal_failure_fixture()
    fig, ax = plt.subplots(figsize=(6.8, 1.8))
    _draw_graph(ax, load_evidence(report)[0], 'C', '#316BA4')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    key = next(text for text in ax.texts if text.get_text().startswith('1  world >'))
    note = next(text for text in ax.texts if text.get_text().startswith('No eligible fresh native candidate'))
    assert key.get_window_extent(renderer).y0 - note.get_window_extent(renderer).y1 >= 5
    plt.close(fig)
    path = tmp_path / 'scripted-terminal-report.json'
    path.write_text(json.dumps(report, sort_keys=True))
    captured, original_close = [], plt.close
    def capture_close(figure=None):
        if hasattr(figure, 'canvas'):
            captured.append(figure)
        else:
            original_close(figure)
    monkeypatch.setattr(plt, 'close', capture_close)
    manifest = make_figure(path, tmp_path / 'scripted-terminal-figure')
    assert all(len(arm['native_loss_path']) == 1 for arm in manifest['arms'])
    complete = captured[-1]
    complete.canvas.draw()
    renderer = complete.canvas.get_renderer()
    footer = next(text for text in complete.texts if text.get_text().startswith('A: accepted decisions.'))
    assert footer.get_window_extent(renderer).x0 >= 0
    assert footer.get_window_extent(renderer).x1 <= complete.bbox.x1 - 2
    for axis in complete.axes:
        for text in axis.texts:
            if text.get_text().startswith('No eligible fresh native candidate'):
                assert text.get_window_extent(renderer).y0 - footer.get_window_extent(renderer).y1 >= 5
        if axis.get_ylabel():
            assert axis.yaxis.label.get_window_extent(renderer).x0 >= 0
    original_close(complete)


def test_actual_cut_comes_only_from_selected_system_not_conceptual_edges():
    report = report_fixture()
    evidence = load_evidence(report)
    generated, original = evidence
    assert len(generated['cut']['internal_nodes']) == 2 and generated['cut']['authored']
    assert len(generated['cut']['edges']) == 5
    assert original['cut']['internal_nodes'] == ['world.selection'] and not original['cut']['authored']
    assert generated['cut']['outgoing_nodes'] == ['world.publication']
    assert graph_cut(report['arms'][generated['id']]['selected_system']) == generated['cut']


@pytest.mark.parametrize('mutation,match', [
    (lambda r: r.pop('classification'), 'classification'),
    (lambda r: r.update(status='running-objective-conditioned-search'), 'terminal'),
    (lambda r: r['arms']['native-joint-v5-throughput'].update(loss_path=[-1, -9]), 'path differs'),
    (lambda r: r['arms']['native-joint-v5-throughput'].update(selected_index=0), 'incumbent'),
    (lambda r: r['arms']['native-joint-v5-throughput'].update(selected_fingerprint='tampered'), 'identity'),
    (lambda r: r['arms']['native-joint-v5-throughput']['audit']['rows'][1].update(status='invalid'), 'numerical loss'),
    (lambda r: r['arms']['native-joint-v5-throughput'].update(authoring_error={'loss': -999}), 'null loss'),
])
def test_mismatched_or_fake_numerical_evidence_rejected(mutation, match):
    report = report_fixture()
    mutation(report)
    with pytest.raises(ValueError, match=match):
        load_evidence(report)


def test_null_technical_failure_not_invented_as_point_and_original_graph_retained():
    report = report_fixture()
    arm = report['arms']['native-joint-v5-throughput']
    utility = report['arms']['native-joint-v5-net-reviewed-utility']
    arm.update(selected_system=deepcopy(utility['selected_system']), selected_fingerprint=utility['selected_fingerprint'], selected_index=0)
    arm['loss_path'] = arm['loss_path'][:1]
    arm['audit']['rows'] = arm['audit']['rows'][:1]
    arm['audit']['loss_path'] = arm['loss_path']
    arm['authoring_error'] = {'proposal_index': 1, 'loss': None, 'error': 'bounded technical drafts failed'}
    report['status'] = 'terminal-with-preserved-failures'
    evidence = load_evidence(report)
    assert [r['loss'] for r in evidence[0]['rows']] == [-1]
    assert not evidence[0]['cut']['authored']


def test_failed_native_observation_is_null_gap_not_zero_or_penalty():
    report = report_fixture()
    arm = report['arms']['native-joint-v5-throughput']
    parent = report['arms']['native-joint-v5-net-reviewed-utility']
    arm['audit']['rows'][1].update(status='invalid', loss=None)
    arm['loss_path'][1] = None
    arm.update(selected_index=0, selected_system=parent['selected_system'], selected_fingerprint=parent['selected_fingerprint'])
    evidence = load_evidence(report)
    assert [row['loss'] for row in evidence[0]['rows']] == [-1, None]


def test_figure_deterministic_bound_and_fixture_cannot_be_paper_asset(tmp_path):
    path, output = tmp_path / 'scripted-report.json', tmp_path / 'scripted-figure'
    path.write_text(json.dumps(report_fixture(), sort_keys=True))
    manifest = make_figure(path, output)
    before = {suffix: output.with_suffix(suffix).read_bytes() for suffix in ('.pdf', '.png', '.manifest.json')}
    assert make_figure(path, output) == manifest
    assert before == {suffix: output.with_suffix(suffix).read_bytes() for suffix in before}
    assert manifest['classification'] == FIXTURE and not manifest['scientific_quality_claim']
    assert all(not arm['authoring_failure_is_loss_point'] for arm in manifest['arms'])
    with pytest.raises(ValueError, match='paper/figures'):
        make_figure(path, tmp_path / 'paper/figures/synthetic-must-not-exist')
