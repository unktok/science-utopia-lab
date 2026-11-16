"""Real immutable source guards, without model/native execution or mock provenance."""
import hashlib
from pathlib import Path

import pytest

from scripts import run_native_priority_fixed_evaluation_v1 as fixed
from scripts import run_native_priority_method_comparison_v1 as method
from utopia.optimization.native_jobs import pinned_revision


ORIGINAL = 'a5be8d3103854368a4bc6ba4c13eff7552e9dd15'
LEGACY_METHOD = '705b5259ad06366f7d178804c6d67ff5ea17cdb4'
RECOVERY = 'utopia/optimization/native_authoring_recovery_v44.py'


def proof(kind):
    if kind == 'method':
        return method.native_sources(ORIGINAL, pinned_revision(method.ROOT))
    return fixed.native_sources(LEGACY_METHOD)


@pytest.mark.parametrize('kind', ['method', 'fixed'])
def test_actual_author_repair_is_explicitly_bound_not_excluded(kind):
    result = proof(kind)
    adapter = result['explicit_native_adapters'][RECOVERY]
    assert adapter['source_commit'] == pinned_revision(method.ROOT)
    assert adapter['current_sha256'] == hashlib.sha256((method.ROOT / RECOVERY).read_bytes()).hexdigest()
    assert adapter['original_sha256'] != adapter['current_sha256']
    assert RECOVERY not in result['author_domain_only_exclusions']
    assert not result['global_semantic_equivalence_claimed']
    for name in ('utopia/simulation.py', 'utopia/optimization/native_factory.py',
                 'utopia/system/native_kernel.py', 'scripts/native_benchmark_physical.py'):
        assert result['literal_files'][name] == hashlib.sha256((method.ROOT / name).read_bytes()).hexdigest()


@pytest.mark.parametrize('kind', ['method', 'fixed'])
@pytest.mark.parametrize('name', [RECOVERY, 'utopia/simulation.py',
                                'utopia/optimization/native_factory.py',
                                    'scripts/native_benchmark_physical.py',
                                    'utopia/optimization/native_component_lab_v1.py',
                                    'utopia/optimization/native_post_edit_feedback_v1.py',
                                    'utopia/optimization/native_workflow_staged_designer_v1.py'])
def test_guard_still_rejects_local_author_or_scientific_drift(kind, name, monkeypatch):
    # Inject only the read result; do not alter this checkout or an active source.
    original_read = Path.read_bytes
    target = method.ROOT / name

    def drift(path):
        raw = original_read(path)
        return raw + b'\n# injected uncommitted byte drift\n' if path == target else raw

    monkeypatch.setattr(Path, 'read_bytes', drift)
    with pytest.raises(ValueError, match='source differs|adapter differs'):
        proof(kind)


def test_same_source_evaluation_needs_no_fabricated_author_adapter():
    result = fixed.native_sources(pinned_revision(fixed.ROOT))
    assert not result.get('explicit_native_adapters')
    assert RECOVERY in result['literal_files']


def test_method_rejects_an_old_adapter_commit_for_the_new_author_bytes():
    with pytest.raises(ValueError, match='explicit versioned native adapter differs'):
        method.native_sources(ORIGINAL, LEGACY_METHOD)
