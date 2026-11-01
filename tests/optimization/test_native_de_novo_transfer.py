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
    # The sealed calibration and its analysis continuation share execution code.
    # HEAD intentionally changes as the native kernel gains migration support;
    # matching an archived baseline to every future HEAD would be incorrect.
    assert runtime_tree('8a114f3') == runtime_tree('951695b')


def test_runtime_identity_excludes_proposers_but_detects_native_changes(monkeypatch):
    import scripts.prepare_native_de_novo_design as driver
    objects = {"utopia/simulation.py": "core-v1", "utopia/optimization/new_proposer.py": "proposal-v1"}
    def git(args, **kwargs):
        if args[1] == "ls-tree":
            return "\n".join(objects)
        return objects[args[-1].split(":", 1)[1]]
    monkeypatch.setattr(driver.subprocess, "check_output", git)
    before = runtime_tree("fixture")
    objects["utopia/optimization/new_proposer.py"] = "proposal-v2"
    assert runtime_tree("fixture") == before
    objects["utopia/simulation.py"] = "core-v2"
    assert runtime_tree("fixture") != before
