"""Static and original-native QA of the explicitly authored pilot example.

The source example is a disclosed external author, not an LLM invention result.
Only the integration test executes native science; HTTP/corpus are scripted.
"""
import pytest

from scripts.author_native_open_estimators_v11 import authored_definition
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_open_examples import open_native_system


def request(parent):
    return {'generation':0,'parent_system':parent.to_dict(),'history':[],
        'history_sha256':digest([])}


def loss():
    return load_loss_spec('research/objectives/losses/native-joint-v5-net-reviewed-utility.json')


def test_static_exact_matched_authorship_and_full_choice_compilation():
    parent=open_native_system('sha256:'+'a'*64)
    left=authored_definition(request(parent),method='blackbox')
    right=authored_definition(request(parent),method='score-control-variate')
    assert left==right
    mixed=GeneratedMixedDesign(parent,left,loss_spec=loss(),seed=42)
    assert len(mixed.policy.assignments)==2
    for assignment in mixed.policy.assignments:
        system,_=mixed.policy.compile_assignment(assignment)
        nodes={n.mechanism_id:n for n in system.mechanisms}
        assert 'review-evidence' in nodes
        assert 'addressed-selection' not in nodes
        assert 'open-memory-router' not in nodes
        assert nodes['world.selection'].implementation=='code.python.v1'
        assert any(e.source_mechanism=='review-evidence' and
            e.target_mechanism=='world.selection' for e in system.connections)
    assert len(mixed.draw(2,version_sha256='static-authored-example'))==2


def test_both_authored_algorithms_execute_original_native_world(tmp_path,fixed_corpus):
    try:
        executor=DockerCodeExecutor()
    except (OSError,CodeExecutionError):
        pytest.skip('existing isolated local executor required')
    parent=open_native_system(executor.image_id)
    definition=authored_definition(request(parent),method='blackbox')
    mixed=GeneratedMixedDesign(parent,definition,loss_spec=loss(),seed=42)
    for index,assignment in enumerate(mixed.policy.assignments):
        system,_=mixed.policy.compile_assignment(assignment)
        seed()
        simulation,calls=make_sim(tmp_path/str(index),native=NativeScienceKernel(system))
        try:
            simulation.run()
            assert simulation.native_system.last_year==6
            assert calls
            events=simulation.native_system.events
            assert any(e.provenance.get('mechanism_id')=='review-evidence' for e in events)
            assert len(simulation.yearly_results)==6
            assert any(row['decisions']['total_accepted'] for row in simulation.yearly_results)
        finally:
            simulation.llm.response_cache.close()
