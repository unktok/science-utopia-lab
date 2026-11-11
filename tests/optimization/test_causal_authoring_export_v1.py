import pytest

from scripts.reports.causal_authoring_assay_v1 import export, usage, literal_patch


def test_usage_keeps_unreported_tokens_unknown_and_nonfinal_length_visible():
    result = usage([{'prompt_tokens':12, 'output_tokens':3, 'elapsed_seconds':1,
                     'done':True,'done_reason':'stop'},
                    {'prompt_tokens':None, 'output_tokens':None, 'elapsed_seconds':None,
                     'done':False, 'done_reason':'length'}])
    assert result['prompt_tokens'] == {'known_sum':12,'unknown_responses':1}
    assert result['output_tokens'] == {'known_sum':3,'unknown_responses':1}
    assert result['nonfinal_responses'] == result['length_terminated_responses'] == 1
    assert result['unknown_http_durations'] == 1


def test_divergent_cold_audits_stop_export_before_any_saved_data(tmp_path):
    one = tmp_path/'one.json'; two = tmp_path/'two.json'
    one.write_text('{}');two.write_text('{"different": true}')
    output = tmp_path/'output'
    with pytest.raises(ValueError, match='cold audits differ'):
        export(tmp_path, one, two, tmp_path, tmp_path, output)
    assert not output.exists()


def test_literal_export_keeps_parameter_and_code_changes_and_reconstructs_whole_candidate():
    from tests.optimization.test_native_causal_design import anchor
    from utopia.system import SystemSpec
    from utopia.system.design_patch import apply_design_patch
    base = anchor(); document = base.to_dict()
    node = next(n for n in document['mechanisms'] if n['mechanism_id'] == 'open-memory-router')
    node['parameters']['program']['parameters']['bias'] = .75
    # A numeric-only edit must not vanish because selector source is unchanged.
    candidate = SystemSpec.from_dict(document)
    patch = literal_patch(base, candidate)
    assert apply_design_patch(base, patch).fingerprint == candidate.fingerprint
    assert len(patch['operations']) == 1 and patch['operations'][0]['path'].endswith('/bias')
    selection = next(n for n in document['mechanisms'] if n['mechanism_id'] == 'world.selection')
    selection['parameters']['code_artifact']['source'] += '\n# exact literal export\n'
    candidate = SystemSpec.from_dict(document)
    patch = literal_patch(base, candidate)
    assert len(patch['operations']) == 2
    assert apply_design_patch(base, patch).fingerprint == candidate.fingerprint
