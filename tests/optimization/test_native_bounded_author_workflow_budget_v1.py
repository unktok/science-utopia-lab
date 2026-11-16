"""Real native document boundary data; no inference or candidate execution."""
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request
from tests.optimization.test_native_bounded_author_context_v45 import frame
from utopia.optimization.native_staged_author_v15 import initial_draft
from utopia.system.design_patch import digest

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'
CASES = [('parent-zero', 61892, 65479), ('parent-terminal', 62755, 66342),
         ('after-feature-write', 62032, 65619)]


@pytest.fixture(autouse=True)
def forbid_candidate_execution(monkeypatch):
    def forbidden(*a, **kw): pytest.fail('boundary regression must never execute generated code')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


def inspected(body):
    state = initial_draft(body)
    steps = [{'step': i, 'status': 'applied', 'errors': [],
        'model_reply': {'output': {'tool': 'read_file', 'filename': 'system.json'}},
        'transition': {'tool': 'read_file', 'ok': True,
            'draft_before_sha256': digest(state), 'draft_after_sha256': digest(state)}} for i in range(3)]
    return state, steps


@pytest.mark.parametrize('name,compact_bytes,legacy_bytes', CASES)
def test_full_document_actually_supplied_must_enable_its_implementation_checkpoint(name, compact_bytes, legacy_bytes):
    doc = json.loads((FIXTURES / (name + '.json')).read_text())
    assert len(json.dumps(doc, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(',', ':')).encode()) == compact_bytes
    assert len(json.dumps(doc, ensure_ascii=False, allow_nan=False).encode()) == legacy_bytes
    body = request(); body['parent_system'] = doc; state, steps = inspected(body)
    prompt, _ = frame(body, state, steps); data = json.loads(prompt)
    flow = data['000_current_turn']['authoring_workflow']
    assert data['literal_current_system'] == doc and flow['literal_current_system_included']
    assert flow['successful_inspections_since_last_document_change'] == 3
    assert flow['phase'] == 'implementation'
