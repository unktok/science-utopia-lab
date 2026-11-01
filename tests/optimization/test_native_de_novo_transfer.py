from scripts.prepare_native_de_novo_design import designer_cache_binding, runtime_tree
from utopia.runtime.checkpointing import validate_binding


def test_designer_cache_has_actual_portable_binding():
    # Pure QA identity; no model calls or native claim.
    value = {'parent_fingerprint': 'QA-parent', 'model': 'QA-model', 'model_digest': 'QA-digest',
        'world': {'corpus_sha256': 'QA-corpus'}, 'seeds': [42], 'mode': 'region'}
    result = validate_binding(designer_cache_binding(value))
    assert result['science_config']['proposal_binding'] == value
    assert result['seed'] == 42


def test_execution_tree_identity_is_stable_for_unchanged_native_runtime():
    assert runtime_tree('8a114f3') == runtime_tree('HEAD')
