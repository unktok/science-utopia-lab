import importlib.util
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_free_source import recorded_selection
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus

from utopia.optimization.native_manifest_inbox import (
    ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox,
)
from utopia.system.code_mechanisms import sha


def request(inbox, **extra):
    return inbox.generate(prompt='Exact objective and world DATA', system_prompt='Free code/graph',
        seed_ctx=('fixed', 1301), max_tokens=4096, temperature=.2,
        response_format={'type': 'json_schema', 'json_object': {'schema': {'type': 'object'}}}, **extra)


def answer(wait, manifest=None):
    response = {'request_sha256': wait.request_sha256,
        'manifest': {'nodes': [], 'rationale': 'explicit fixture, not invention'} if manifest is None else manifest,
        'authoring': {'kind': 'codex-agent', 'identity': 'scripted QA only'}}
    wait.response_path.parent.mkdir(parents=True, exist_ok=True)
    wait.response_path.write_text(json.dumps(response))
    return response


def test_exact_request_pending_response_consumption_resume_and_no_fake_loss(tmp_path):
    inbox = ManifestInbox(tmp_path)
    with pytest.raises(ExternalAuthoringPending) as pending:
        request(inbox)
    wait = pending.value
    saved = json.loads(wait.request_path.read_text())
    assert sha(saved) == wait.request_sha256
    assert saved['request']['seed_ctx'] == ['fixed', 1301]
    assert saved['request']['max_tokens'] == 4096 and saved['request']['temperature'] == .2
    assert wait.to_dict()['technical_failure'] is False and wait.to_dict()['loss'] is None
    response = answer(wait)
    assert request(inbox) == (response['manifest'], [])
    assert request(ManifestInbox(tmp_path)) == (response['manifest'], [])
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    audit = audit_manifest_inbox(tmp_path)
    assert audit['requests'][0]['status'] == 'consumed' and audit['model_calls'] == 0
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    response['manifest']['rationale'] = 'changed after consuming'
    wait.response_path.write_text(json.dumps(response))
    with pytest.raises(ValueError, match='consumed external'):
        request(inbox)
    with pytest.raises(ValueError, match='consumed external'):
        ManifestInbox(tmp_path)


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(request_sha256='wrong'),
    lambda r: r.update(authoring={'kind': 'unrecorded-network-provider'}),
    lambda r: r.update(extra='unbound metadata'),
    lambda r: r.update(manifest='not a manifest'),
])
def test_response_must_match_exact_request_and_authoring_contract(tmp_path, mutation):
    inbox = ManifestInbox(tmp_path)
    with pytest.raises(ExternalAuthoringPending) as pending:
        request(inbox)
    response = answer(pending.value)
    mutation(response)
    pending.value.response_path.write_text(json.dumps(response))
    with pytest.raises(ValueError, match='exact request binding'):
        request(inbox)
    assert not list((tmp_path / 'consumed').glob('*.json'))


def test_changed_generation_settings_get_different_requests_and_no_network(tmp_path):
    inbox = ManifestInbox(tmp_path)
    digests = []
    for seed in (42, 43):
        with pytest.raises(ExternalAuthoringPending) as wait:
            inbox.generate(prompt='same prompt', seed_ctx=(seed,))
        digests.append(wait.value.request_sha256)
    assert len(set(digests)) == 2


def test_consumed_raw_bytes_are_also_bound_not_only_canonical_json(tmp_path):
    inbox = ManifestInbox(tmp_path)
    with pytest.raises(ExternalAuthoringPending) as wait:
        request(inbox)
    response = answer(wait.value)
    request(inbox)
    wait.value.response_path.write_text(json.dumps(response, indent=4))
    with pytest.raises(ValueError, match='consumed external'):
        ManifestInbox(tmp_path)


def test_symlink_response_is_not_consumed(tmp_path):
    inbox = ManifestInbox(tmp_path / 'inbox')
    with pytest.raises(ExternalAuthoringPending) as wait:
        request(inbox)
    real = tmp_path / 'other.json'
    real.write_text('{}')
    wait.value.response_path.parent.mkdir(parents=True)
    wait.value.response_path.symlink_to(real)
    with pytest.raises(ValueError, match='bounded regular'):
        request(inbox)


def driver_module():
    spec = importlib.util.spec_from_file_location('external_driver',
        Path(__file__).resolve().parents[2] / 'scripts/run_external_native_objectives_v5.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Controller:
    def __init__(self):
        self.state = {'records': [{'observation': {'loss': 0}}], 'pending': None}
        self.calls = 0
    def advance(self, *, simulation_factory, proposer):
        self.calls += 1
        proposer()
        self.state['records'].append({'observation': {'loss': 1}})


def test_pending_one_arm_does_not_prevent_other_request_or_fabricate_completion(tmp_path):
    controllers = [Controller(), Controller()]
    inboxes = [ManifestInbox(tmp_path / arm) for arm in ['a', 'b']]
    errors = {}
    result = driver_module().advance_arms(['a', 'b'], controllers,
        [lambda inbox=i: request(inbox) for i in inboxes], simulation_factory=None, budget=3, errors=errors)
    assert result['status'] == 'waiting-for-external-authoring' and not result['terminal']
    assert set(result['pending_external_authoring']) == {'a', 'b'}
    assert errors == {} and [c.calls for c in controllers] == [1, 1]
    assert [len(c.state['records']) for c in controllers] == [1, 1]


def test_driver_resumes_existing_baseline_and_handles_exhausted_budget_without_score(tmp_path):
    controllers = [Controller(), Controller()]
    def fail():
        raise ValueError('bounded region technical drafts exhausted; no native loss fabricated')
    errors = {}
    result = driver_module().advance_arms(['failed', 'complete'], controllers,
        [fail, lambda: None], simulation_factory=None, budget=3, errors=errors)
    assert result['terminal'] and result['status'] == 'terminal-with-preserved-failures'
    assert errors['failed']['loss'] is None
    assert [len(c.state['records']) for c in controllers] == [1, 3]


def test_external_manifest_exactly_reaches_real_docker_and_original_native_world(recorded_selection, tmp_path):
    from tests.optimization.test_native_region_ir import fixture_ir
    from tests.optimization.test_native_world import loss_spec
    from utopia.optimization.native_region_proposer_v5a2 import NativeBoundaryRegionProposer
    campaign, factory, executor, provider = recorded_selection
    inbox = ManifestInbox(tmp_path / 'native-inbox')
    proposer = NativeBoundaryRegionProposer(inbox, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'native-proposals')
    baseline_hash = sha(campaign.state['records'][0])
    with pytest.raises(ExternalAuthoringPending) as wait:
        campaign.advance(simulation_factory=factory, proposer=proposer)
    assert len(campaign.state['records']) == 1 and campaign.state['pending'] is None
    assert not list((tmp_path / 'native-proposals').glob('region-1-*.json'))
    actual_manifest = fixture_ir()
    response = answer(wait.value, actual_manifest)
    result = campaign.advance(simulation_factory=factory, proposer=proposer)
    assert result['observation']['status'] == 'complete'
    assert len(campaign.state['records']) == 2 and sha(campaign.state['records'][0]) == baseline_hash
    receipt = json.loads((tmp_path / 'native-proposals/region-1-0.json').read_text())
    assert receipt['generated'] == actual_manifest and len(receipt['runs']) == 6
    assert receipt['generated_source_sha256s'] == {n['id']: sha(n['python_code']) for n in actual_manifest['nodes']}
    consumed = json.loads((tmp_path / 'native-inbox/consumed' / (wait.value.request_sha256 + '.json')).read_text())
    assert consumed['manifest_sha256'] == sha(receipt['generated'])
    assert consumed['response_sha256'] == sha(response)
