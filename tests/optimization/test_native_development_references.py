"""Synthetic reference arithmetic; no claims about measured native superiority."""
import pytest

from tests.optimization.test_native_initial_evidence import donor,WORLD
from tests.optimization.test_native_world import loss_spec
from tests.optimization.test_native_adaptive_search import STRATEGIES
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_development_references import build_context,validate_context
from utopia.system.native_kernel import legacy_world_system
from utopia.system.design_patch import clone,digest


def context(monkeypatch):
    monkeypatch.setattr('utopia.optimization.native_development_references.verify_native_observation',lambda *a:None)
    records=donor()['runs']['fixture-arm']['records'][:2]
    pairs=[{'suggestion':clone(r['draws'][0]['suggestion']),'observation':clone(r['observations'][0])} for r in records]
    for value,pair in zip([9.,1.],pairs):
        pair['observation']['metadata']['measurements'][0]['metrics']['native.common_content_utility_sum']={
            'status':'measured','value':value}
    # Native count loss is unchanged by adding the separately declared metric.
    return build_context(pairs,world=WORLD,seeds=[42],loss_spec=loss_spec())


def test_objective_specific_best_known_reference_enters_parent_without_becoming_a_submitted_candidate(tmp_path,monkeypatch):
    bank=context(monkeypatch);before=clone(bank);parents=[]
    for name,loss in [('count',loss_spec()),('content',loss_spec('native.common_content_utility_sum'))]:
        c=NativeAdaptiveDesignCampaign(tmp_path/name,initial_system=legacy_world_system(),loss_spec=loss,seeds=[42],
            world_binding=WORLD,strategies=STRATEGIES,mode='blackbox',development_references=bank)
        request=c._request([],c._strategy_initial(),1)
        selected=next(p for p in request['observations'] if p['observation']['observation_id']==request['based_on_observation_id'])
        parents.append(selected['suggestion']['suggestion_id'])
        assert len(request['observations'])==2 and len(request['developer_reference_context']['summary'])==2
        assert not c.state['records'] and c.state['pending'] is None
        assert all(p['observation']['metadata']['development_reference']['not_a_new_candidate_or_world'] for p in request['observations'])
    assert parents==[bank['pairs'][1]['suggestion']['suggestion_id'],bank['pairs'][0]['suggestion']['suggestion_id']]
    assert bank==before


@pytest.mark.parametrize('damage',['world','seeds','loss','duplicate','journal-envelope','fingerprint','measurement-id'])
def test_changed_or_misbound_common_references_are_not_silently_imported(monkeypatch,damage):
    bank=context(monkeypatch)
    if damage=='world':
        with pytest.raises(ValueError,match='world differs'):validate_context(bank,target_world={**WORLD,'source_commit':'another'})
        return
    if damage=='seeds':
        with pytest.raises(ValueError,match='seeds differ'):validate_context(bank,target_seeds=[43])
        return
    if damage=='loss':bank['pairs'][0]['observation']['loss']=999.
    if damage=='duplicate':bank['pairs'][1]=clone(bank['pairs'][0])
    if damage=='journal-envelope':bank['pairs'][0]['observation']['content_sha256']='not a canonical observation'
    if damage=='fingerprint':bank['pairs'][0]['observation']['metadata']['system_fingerprint']='another system'
    if damage=='measurement-id':bank['pairs'][0]['observation']['metadata']['measurements'][0]['run_id']='another world'
    bank['content_sha256']=digest({k:v for k,v in bank.items() if k!='content_sha256'})
    with pytest.raises(ValueError):validate_context(bank)
