import copy
import hashlib
import json

import pytest

from scripts.figures.native_design_evidence import AUDIT, ENVELOPE, load_evidence


def evidence():
    return json.loads(AUDIT.read_text()), json.loads(ENVELOPE.read_text())


def edited(envelope, change):
    envelope = copy.deepcopy(envelope)
    payload = json.loads(envelope["payload_json"])
    change(payload)
    envelope["payload_json"] = json.dumps(payload)
    envelope["payload_sha256"] = hashlib.sha256(envelope["payload_json"].encode()).hexdigest()
    return envelope


def test_actual_native_figure_evidence():
    history, losses = load_evidence(*evidence())
    assert len(history) == 31
    assert losses == [0, -3]


def test_modified_raw_evidence_rejected():
    audit, envelope = evidence()
    envelope["payload_json"] += " "
    with pytest.raises(ValueError, match="hash mismatch"):
        load_evidence(audit, envelope)


@pytest.mark.parametrize("edit, message", [
    (lambda p: p["relaxation"].update(full_native_world_autograd=True), "full-world"),
    (lambda p: p["systems"][1].update(native_loss=-100), "completion/loss"),
    (lambda p: p["relaxation"]["history"][-1]["parameters"]["addressed-selection"].update(bias=100), "not installed"),
    (lambda p: p["relaxation"]["history"].pop(), "30-step"),
    (lambda p: p["source"]["seeds"].append(999), "binding mismatch"),
])
def test_rehashed_but_misrepresented_evidence_rejected(edit, message):
    audit, envelope = evidence()
    with pytest.raises(ValueError, match=message):
        load_evidence(audit, edited(envelope, edit))
