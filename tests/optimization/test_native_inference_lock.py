from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading
import time
import pytest
from utopia.optimization.native_factory import serialize_native_http


def test_independent_pipeline_wrappers_share_one_active_inference_slot(tmp_path):
    active = 0
    maximum = 0
    count_lock = threading.Lock()
    def callback(**payload):
        nonlocal active, maximum
        with count_lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(.025)  # bounded numerical concurrency QA, no LLM request
        with count_lock:
            active -= 1
        return payload
    models = [SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=callback)))) for _ in range(2)]
    for model in models:
        serialize_native_http(model, tmp_path / 'shared.lock')
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda i: models[i].client.chat.completions.create(item=i), range(2)))
    assert maximum == 1 and results == [{'item': 0}, {'item': 1}]


def test_transport_exception_releases_shared_slot(tmp_path):
    attempts = []
    def callback(**payload):
        attempts.append(payload)
        if len(attempts) == 1:
            raise ValueError('QA injected transport failure')
        return True
    model = SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=callback))))
    serialize_native_http(model, tmp_path / 'shared.lock')
    with pytest.raises(ValueError):
        model.client.chat.completions.create()
    assert model.client.chat.completions.create() is True
