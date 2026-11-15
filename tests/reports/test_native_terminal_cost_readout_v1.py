"""Read-only export checks on an already closed SCRIPTED software fixture.

No new world, generated-source execution, model dispatch or heavy full-path QA.
Explicit copied software cost aliases test file binding, not independent cost evidence.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_terminal_cost_pilot_v1 as reader
from utopia.optimization.native_numeric_designer import checked


def test_request_position_preserves_unknown_phase_and_empty_tail():
    wires = [{'year': 4, 'payload': {'response_format': {'json_schema': {'name': 'SCRIPTED-name'}}}}]
    assert reader.request_position(wires, 1) is None
    result = reader.request_position(wires, 0)
    assert result['year'] == 4 and result['response_schema'] == 'SCRIPTED-name'
    assert result['native_phase'] is None


def test_paired_readout_continuation_binds_same_cost_pair_and_original_scientific_source(tmp_path, monkeypatch):
    from scripts import finish_native_terminal_cost_readouts_v1 as finish
    called = {}
    monkeypatch.setattr(finish, 'finish', lambda args, **kwargs: called.update(kwargs))
    args = SimpleNamespace(analysis=tmp_path / 'closed-audits', frozen_source=tmp_path / 'scientific-source')
    finish.run(args)
    assert called['plan_schema'] == 'scienceutopia.native-terminal-cost-pilot.v1.plan'
    assert called['preceding_schema'] == 'scienceutopia.native-terminal-cost-pilot-finish.v1'
    assert called['report_module'] == 'scripts.reports.native_terminal_cost_pilot_v1'
    assert called['report_extra_arguments'] == ('--frozen-source', str(args.frozen_source),
        '--cost-one', str(args.analysis / 'costs-1.json'), '--cost-two', str(args.analysis / 'costs-2.json'))


@pytest.mark.skipif(not os.environ.get('SCIENCE_UTOPIA_TERMINAL_READOUT_SOFTWARE_ROOT'),
                   reason='explicit existing closed SCRIPTED software input required')
def test_two_literal_readouts_preserve_cost_loophole_content_and_no_gain_gate():
    root = Path(os.environ['SCIENCE_UTOPIA_TERMINAL_READOUT_SOFTWARE_ROOT']).resolve()
    frozen = Path(os.environ['SCIENCE_UTOPIA_TERMINAL_READOUT_FROZEN_SOURCE']).resolve()
    with tempfile.TemporaryDirectory(prefix='terminal-cost-readout-software-') as directory:
        directory = Path(directory)
        for number in (1, 2):
            shutil.copyfile(root / ('audit-retained.json' if number == 1 else 'audit-retained-2.json'),
                            directory / f'audit-{number}.json')
            # The original public test computes/asserts both cost projections,
            # but saves one. These aliases are explicitly not two new analyses.
            shutil.copyfile(root / 'cost-retained.json', directory / f'cost-{number}.json')
        options = dict(run=root / 'pilot', frozen_source=frozen,
            audit_one=directory / 'audit-1.json', audit_two=directory / 'audit-2.json',
            cost_one=directory / 'cost-1.json', cost_two=directory / 'cost-2.json')
        outputs = [directory / f'export-{n}' for n in (1, 2)]
        for out in outputs:
            reader.export(SimpleNamespace(**options, output=out))
        assert all((outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
                   for name in ('report.json', 'controls.csv', 'manifest.json'))
        report = checked(json.loads((outputs[0] / 'report.json').read_text()))
        a, b = report['worlds']
        assert [a['resource_cost'], b['resource_cost']] == [200, 160]
        assert [a['uncollected_activity_cost'], b['uncollected_activity_cost']] == [0, 40]
        assert a['requested_activity_cost'] == b['requested_activity_cost'] == 200
        assert [a['final_active_authors'], b['final_active_authors']] == [5, 1]
        assert [a['final_resources'], b['final_resources']] == [30, 70]
        assert report['loss_contrast_control_minus_reference'] == {
            'content_loss': 0, 'collected_cost': -40, 'resource_coefficient': 0.1,
            'resource_aware_content_loss': -4}
        assert a['scores']['throughput'] == b['scores']['throughput'] == -20
        assert report['accepted_content_overlap']['common']['occurrences'] == 20
        assert all(event['phase'] == 162 for world in (a, b) for event in world['native_transfers'])
        assert report['new_model_calls'] == report['new_code_executions'] == 0
        assert not report['automatic_invention'] and not report['publication_ready']
        with pytest.raises(ValueError, match='fresh readout'):
            reader.export(SimpleNamespace(**options, output=outputs[0]))
        with pytest.raises(ValueError, match='distinct matching'):
            reader.export(SimpleNamespace(**{**options, 'cost_two': options['cost_one']}, output=directory / 'invalid'))
