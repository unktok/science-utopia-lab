"""SCRIPTED technical checks: copy equality is diagnostic, literal receipt is not."""
import json

import pytest

from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from tests.optimization.test_native_authoring_ir import BINDING, request
from utopia.optimization import native_designer_preflight as p
from utopia.optimization.native_designer_tools_v25 import action_from_body, response_message_from_action
from utopia.system.design_patch import digest


class ChangedSourceSession(ScriptedSession):
    mutation = 'whitespace'

    def post(self, url, **kwargs):
        response = super().post(url, **kwargs)
        action = action_from_body(response.body)
        if action['tool'] == 'edit_fields' and action['field_updates'][0]['field_name'] == 'source':
            source = action['field_updates'][0]['value']
            if self.mutation == 'whitespace':
                action['field_updates'][0]['value'] = source + '          '
            elif self.mutation == 'syntax':
                action['field_updates'][0]['value'] = 'def broken(:\n'
            elif self.mutation == 'permission':
                action['field_updates'][0]['field_name'] = 'not_an_existing_field'
            elif self.mutation == 'schema':
                action['field_updates'] = 'not-an-array'
            elif self.mutation == 'tool':
                action = {'tool': 'validate'}
            message = response_message_from_action(action)
            response = Response({**response.body, 'message': {**message,
                'thinking': response.body['message']['thinking']}})
        return response


def run(tmp_path, monkeypatch, *, scope=p.EXECUTION_SCOPE, mutation='whitespace'):
    ChangedSourceSession.mutation = mutation
    ChangedSourceSession.calls = []
    monkeypatch.setattr('requests.Session', ChangedSourceSession)
    directory = tmp_path / (scope + '-' + mutation)
    result = p.run_calibration(directory, request=request(), provider=BINDING, scope=scope)
    return directory / 'certificate.json', result


def test_actual_source_is_preserved_applied_and_cold_replayed_despite_copy_mismatch(tmp_path, monkeypatch):
    path, result = run(tmp_path, monkeypatch)
    assert result['all_controls_passed']
    rows = [row for row in result['records'] if not row['copy_diagnostic']['exact_match']]
    assert len(rows) == 1
    row = rows[0]
    actual = action_from_body(json.loads(row['transport']['raw_http_response']))
    assert digest(actual) == digest(row['output'])
    assert actual['field_updates'][0]['value'].endswith('          ')
    assert row['receipt']['ok'] and row['copy_diagnostic']['actual_sha256'] == digest(actual)
    count = len(ChangedSourceSession.calls)
    checked = p.require_certificate(path, BINDING, protocol='staged-v15', scope=p.EXECUTION_SCOPE)
    assert checked['readiness_scope'] == p.EXECUTION_SCOPE
    assert checked['exact_copy_matches'] == checked['controls'] - 1
    assert len(ChangedSourceSession.calls) == count
    with pytest.raises(ValueError, match='protocol/runtime/backend'):
        p.require_certificate(path, BINDING, protocol='staged-v15')


def test_legacy_strict_copy_still_fails_and_cannot_be_promoted(tmp_path, monkeypatch):
    path, result = run(tmp_path, monkeypatch, scope=p.LITERAL_SCOPE)
    assert not result['all_controls_passed']
    assert 'literal output differs' in result['records'][-1]['error']
    with pytest.raises(ValueError):
        p.require_certificate(path, BINDING, protocol='staged-v15', scope=p.EXECUTION_SCOPE)


@pytest.mark.parametrize('mutation', ['syntax', 'permission', 'schema', 'tool'])
def test_technical_failures_still_stop_without_retry(tmp_path, monkeypatch, mutation):
    path, result = run(tmp_path, monkeypatch, mutation=mutation)
    assert not result['all_controls_passed']
    assert len(result['records']) < len(result['plan']['cases'])
    assert len(ChangedSourceSession.calls) == len(result['records'])
    with pytest.raises(ValueError):
        p.require_certificate(path, BINDING, protocol='staged-v15', scope=p.EXECUTION_SCOPE)


@pytest.mark.parametrize('mutation', ['diagnostic', 'parsed-output', 'raw-partial', 'provider'])
def test_rehashed_new_scope_certificate_cannot_hide_raw_or_diagnostic_changes(tmp_path, monkeypatch, mutation):
    path, result = run(tmp_path, monkeypatch)
    row = result['records'][0]
    if mutation == 'diagnostic':
        row['copy_diagnostic']['exact_match'] = False
    elif mutation == 'parsed-output':
        row['output']['operations'][0]['value'] = 18
    elif mutation == 'raw-partial':
        body = row['transport']['response_payload']
        body['done'] = False
        row['transport']['raw_http_response'] = json.dumps(body)
    else:
        result['plan']['provider']['model_digest'] = '0' * 64
    result['content_sha256'] = digest({k: v for k, v in result.items() if k != 'content_sha256'})
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError):
        p.require_certificate(path, BINDING, protocol='staged-v15', scope=p.EXECUTION_SCOPE)


def test_role_bound_production_rechecks_explicit_scope_before_each_post(monkeypatch):
    from tests.optimization.test_native_search_v14 import BINDING as WORLD_BINDING
    from utopia.optimization.native_designer_roles_v38 import LocalRoleBoundDesignerModel, LOCAL_DESIGNER_IDENTITIES
    binding = {**WORLD_BINDING, 'model': 'qwen3.6:35b-mlx-64k',
        'model_digest': LOCAL_DESIGNER_IDENTITIES['qwen3.6:35b-mlx-64k']}
    seen = []
    def require(path, provider, **kwargs):
        seen.append((path, provider, kwargs['scope']))
        raise ValueError('SCRIPTED rejected certificate before dispatch')
    monkeypatch.setattr(p, 'require_certificate', require)
    model = LocalRoleBoundDesignerModel(binding, preflight_certificate='operator-certificate',
        readiness_scope=p.EXECUTION_SCOPE)
    with pytest.raises(ValueError, match='before dispatch'):
        model.generate(prompt='not sent', system_prompt='not sent', seed_ctx=[],
            max_tokens=8192, temperature=.6, response_format={})
    assert seen == [('operator-certificate', binding, p.EXECUTION_SCOPE)]


def test_new_campaign_explicitly_declares_execution_scope_without_changing_scientists():
    from tests.optimization.test_native_search_v14 import BINDING as WORLD_BINDING, REVISION
    from scripts.run_native_designer_roles_v38 import build_plan
    from utopia.optimization.native_designer_roles_v38 import LOCAL_DESIGNER_IDENTITIES
    from utopia.system.native_open_examples import open_native_system
    designer = {**WORLD_BINDING, 'model': 'qwen3.6:35b-mlx-64k',
        'model_digest': LOCAL_DESIGNER_IDENTITIES['qwen3.6:35b-mlx-64k']}
    plan = build_plan(source_commit=REVISION, initial_system=open_native_system(WORLD_BINDING['image_id']).to_dict(),
        provider_binding=WORLD_BINDING, designer_provider_binding=designer, runtime_seed_binding={})
    assert plan['readiness_scope'] == p.EXECUTION_SCOPE
    assert plan['engineering_revision'] == 'v39-a1'
    assert plan['provider_binding'] == WORLD_BINDING
    assert plan['budget']['scheduled_native_slots'] == 8
