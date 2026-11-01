from copy import deepcopy
import json
from pathlib import Path

import pytest
from scripts.figures.native_open_source import load_evidence

ROOT = Path(__file__).resolve().parents[2]


def test_actual_native_source_path_and_unchanged_generated_program():
    audit = json.loads((ROOT / 'research/results/native-open-source-v3.json').read_text())
    spec = json.loads((ROOT / 'research/artifacts/native-open-source-v3-selected-system.json').read_text())
    assert load_evidence(audit, spec) == ([-1., -1., -3.], 2.5)
    bad = deepcopy(audit)
    bad['rows'][-1]['loss'] = -100.
    with pytest.raises(ValueError, match='loss evidence'):
        load_evidence(bad, spec)
    bad_spec = deepcopy(spec)
    next(n for n in bad_spec['mechanisms'] if n['mechanism_id'] == 'world.selection')['parameters']['code_artifact']['source'] += '\n# edited'
    with pytest.raises(ValueError, match='system identity'):
        load_evidence(audit, bad_spec)
