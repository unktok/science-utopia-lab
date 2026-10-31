import copy
import hashlib
import json
from types import SimpleNamespace

from utopia.optimization.native_factory import record_native_http
from utopia.runtime.checkpointing import canonical_json


def test_actual_http_payload_recorder_does_not_change_model_request(tmp_path):
    received = []
    def callback(**payload):
        received.append(copy.deepcopy(payload))
        return 'actual response'
    model = SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=callback))))
    sim = SimpleNamespace(native_system=SimpleNamespace(_frame={'year': 2}))
    path = tmp_path / 'wire.jsonl'
    record_native_http(model, sim, path)
    request = {'model': 'fixed-model', 'messages': [{'role': 'user', 'content': 'observed institutional context'}], 'extra_body': {'seed': 1}}
    before = copy.deepcopy(request)
    assert model.client.chat.completions.create(**request) == 'actual response'
    assert request == before and received == [before]
    row = json.loads(path.read_text())
    assert row['year'] == 2
    assert row['payload'] == before
    assert row['payload_sha256'] == hashlib.sha256(canonical_json(before).encode()).hexdigest()
