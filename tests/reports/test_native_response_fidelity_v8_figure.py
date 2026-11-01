import json
from pathlib import Path

import pytest

from scripts.figures.native_response_fidelity_v8 import create
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_scripted_native_fidelity_graph_is_scoped_and_hash_bound(tmp_path):
    source = ROOT/'research/results/native-response-fidelity-v8-scripted.json'
    receipt = create(source, tmp_path/'qa')
    assert receipt['classification'] == 'scripted-fixture-not-native-results'
    assert receipt['report_sha256'] == file_sha256(source)
    assert receipt['new_model_calls'] == receipt['new_native_worlds'] == 0
    assert not receipt['native_jacobian_claim']
    for output in receipt['outputs'].values():
        assert file_sha256(output['path']) == output['sha256']


@pytest.mark.parametrize('key,value,match', [
    ('native_LLM_Jacobian_verified', True, 'explicitly scoped'),
    ('new_live_Qwen_calls', 1, 'explicitly scoped'),
    ('endpoints', [], 'seven-world'),
    ('content_sha256', 'bad', 'hash-bound'),
])
def test_mislabelled_or_incomplete_native_qa_fails_closed(tmp_path, key, value, match):
    data = json.loads((ROOT/'research/results/native-response-fidelity-v8-scripted.json').read_text())
    data[key] = value
    if key != 'content_sha256':
        data['content_sha256'] = digest({k: v for k, v in data.items() if k != 'content_sha256'})
    source = tmp_path/'report.json'
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=match):
        create(source, tmp_path/'qa')
