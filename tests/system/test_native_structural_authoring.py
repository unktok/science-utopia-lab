"""Structural ABI units and original six-year scientific-world/Docker QA.

Only researcher HTTP and retrieval/corpus are scripted. These are engineering
tests, never real Qwen, objective improvement or causal-benefit evidence.
"""
from copy import deepcopy

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim
from utopia.runtime.checkpointing import PortableStop
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.design_patch import apply_design_patch, make_patch
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_open_examples import open_native_system
from utopia.system.native_structural_authoring import (explicit_graph_patch, factor_operations,
                                                       native_authoring_contract)
from utopia.system.native_structural_example import (ADAPTER_SOURCE, MARKER, PLANNER_SOURCE,
                                                     structural_agenda_patch)


IMAGE = 'sha256:' + 'a'*64


def candidate(parent, **kwargs):
    return apply_design_patch(parent,structural_agenda_patch(parent,IMAGE,**kwargs))


def test_complete_explicit_transaction_preserves_original_phases_and_exact_source():
    parent=open_native_system(IMAGE)
    before=deepcopy(parent.to_dict())
    result=candidate(parent)
    assert parent.to_dict()==before
    ids={n.mechanism_id for n in result.mechanisms}
    assert {'agenda-planner','agenda-commands','agenda-effects'} <= ids
    assert 'open-source' not in ids and 'open-domain-actions' not in ids
    assert len(result.mechanisms)==len(parent.mechanisms)+1
    assert len(result.connections)!=len(parent.connections)
    for node in parent.mechanisms:
        if node.implementation.startswith(('native.phase.','native.activity.')):
            changed=next(n for n in result.mechanisms if n.mechanism_id==node.mechanism_id)
            assert changed.implementation==node.implementation
            assert changed.parameters==node.parameters
    code={n.mechanism_id:n.parameters['code_artifact']['source'] for n in result.mechanisms
          if n.implementation=='code.python.v1'}
    assert code['agenda-planner']==PLANNER_SOURCE and code['agenda-commands']==ADAPTER_SOURCE
    contract=native_authoring_contract(result)
    assert contract['system']==result.to_dict()
    assert contract['parent_fingerprint']==result.fingerprint
    assert contract['python_abi']['input_access']=="context['inputs'][PORT]"
    phase={s.mechanism_id:s.phase for s in result.schedules}
    assert phase['world.open']<phase['agenda-planner']<phase['agenda-commands']<phase['agenda-effects']<phase['world.research']


def test_missing_incident_edges_schedules_and_typo_disconnect_are_not_repaired():
    parent=open_native_system(IMAGE)
    doc=parent.to_dict()
    with pytest.raises(ValueError):
        explicit_graph_patch(parent,remove_nodes=['open-source'],schedules=doc['schedules'])
    incident=[e for e in doc['connections'] if 'open-source' in (e['source_mechanism'],e['target_mechanism'])]
    with pytest.raises(ValueError):
        explicit_graph_patch(parent,remove_nodes=['open-source'],disconnect=incident,schedules=doc['schedules'])
    typo={**incident[0],'source_port':'unwritten-source-port'}
    with pytest.raises(ValueError,match='does not exist'):
        explicit_graph_patch(parent,disconnect=[typo],schedules=doc['schedules'])
    with pytest.raises(ValueError,match='ambiguous'):
        explicit_graph_patch(parent,remove_nodes=['open-source'],put_nodes=[next(n for n in doc['mechanisms']
            if n['mechanism_id']=='open-source')],schedules=doc['schedules'])


def test_factor_choice_parent_is_compiled_base_not_pre_base():
    parent=open_native_system(IMAGE)
    base=candidate(parent)
    index=next(i for i,n in enumerate(base.mechanisms) if n.mechanism_id=='agenda-planner')
    ops=[{'op':'replace','path':f'/mechanisms/{index}/parameters/assigned_authors','value':2}]
    patch=make_patch(base,ops)
    assert factor_operations(base,patch)==ops
    with pytest.raises(ValueError,match='parent'):
        factor_operations(base,make_patch(parent,ops))
    # Caller code is not a policy catalogue: an arbitrary literal replacement is
    # preserved unchanged and does not run while compiling either API.
    source="def step(context):\n    raise RuntimeError('not executed during authoring')\n"
    authored=candidate(parent,planner_source=source)
    assert next(n for n in authored.mechanisms if n.mechanism_id=='agenda-planner').parameters['code_artifact']['source']==source


def test_new_multinode_institution_changes_real_native_actions_and_cold_reopens(tmp_path,fixed_corpus,monkeypatch):
    monkeypatch.setattr('time.time',lambda:1234567890.)
    executor=DockerCodeExecutor(timeout=60.)
    parent=open_native_system(executor.image_id)
    design=apply_design_patch(parent,structural_agenda_patch(parent,executor.image_id))
    seed()
    reference,calls=make_sim(tmp_path/'reference',native=NativeScienceKernel(design,code_executor=executor))
    reference.run()
    kernel=reference.native_system
    assert kernel.last_year==6
    assert kernel.open_domain_state['actors']['agenda-board']['state']['cycles']==6
    assert len(kernel.open_domain_state['artifacts'])==6
    projects=[e for e in kernel.events if e.event_type=='native.domain.project_applied']
    assert len(projects)==6
    assert all(e.payload['assignment']['detailed_focus'].startswith(MARKER) for e in projects)
    assert any(MARKER in str(payload) for _,payload in calls)
    assert kernel.graph_checkpoint['mechanism_states']['agenda-planner']['years']==6
    seed()
    interrupted,_=make_sim(tmp_path/'restart',native=NativeScienceKernel(design,code_executor=executor),after_effects=True)
    with pytest.raises(PortableStop):interrupted.run()
    interrupted.llm.response_cache.close()
    resumed,_=make_sim(tmp_path/'restart',native=NativeScienceKernel(design,code_executor=executor))
    resumed.run()
    assert science_snapshot(resumed)==science_snapshot(reference)
    assert resumed.native_system.to_dict()==kernel.to_dict()
    # A distinct authored parameter changes actual project-writing counts, not
    # only graph labels. Same original six-year scientific lifecycle runs.
    two=apply_design_patch(parent,structural_agenda_patch(parent,executor.image_id,assigned_authors=2))
    seed()
    variant,variant_calls=make_sim(tmp_path/'two',native=NativeScienceKernel(two,code_executor=executor))
    variant.run()
    assert len([e for e in variant.native_system.events if e.event_type=='native.domain.project_applied'])==12
    assert len([1 for (ctx,_,_),p in calls if ctx[:2]==('phase1_directions',1)])==3
    assert len([1 for (ctx,_,_),p in variant_calls if ctx[:2]==('phase1_directions',1)])==2
    for sim in (reference,resumed,variant):sim.llm.response_cache.close()
