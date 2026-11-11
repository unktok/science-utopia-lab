"""Original native loop with scripted critic; not actual objective-search results."""
import pytest

from tests.optimization.test_native_adaptive_search import PROVENANCE,fail_factory
from tests.optimization.test_native_world import loss_spec
from tests.optimization.test_common_content_observer import Backend,contract
from tests.runtime.test_portable_checkpoint_integration import BINDING,seed,fixed_corpus
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.common_content_observer import CommonContentObserver,ObserverCompletionUnknown
from utopia.system.native_kernel import legacy_world_system,NativeScienceKernel
from utopia.system.design_patch import clone,digest


def campaign(path,instrument=None,*,metric='native.common_content_utility_sum'):
    world={'source_commit':'adaptive-measurement-SCRIPTED-QA','model_digest':BINDING['model_revision'],
        'corpus_sha256':BINDING['corpus_sha256']}
    if instrument is not None:world['measurement_adapter_contract']=clone(instrument)
    return NativeAdaptiveDesignCampaign(path,initial_system=legacy_world_system(),loss_spec=loss_spec(metric),
        seeds=[42],world_binding=world,strategies={'invent':PROVENANCE},mode='blackbox',seed=42)


@pytest.mark.parametrize('kind',['missing','wrong','undeclared','not-callable'])
def test_instrument_mismatch_stops_before_generation_or_native_execution(tmp_path,kind):
    declared={'SCRIPTED':'instrument'};c=campaign(tmp_path,None if kind=='undeclared' else declared)
    kwargs={'measurement_adapter':lambda *a:None,'measurement_contract':declared}
    if kind=='missing':kwargs={}
    if kind=='wrong':kwargs['measurement_contract']={'SCRIPTED':'another'}
    if kind=='not-callable':kwargs['measurement_adapter']='candidate-provided function text'
    with pytest.raises(ValueError,match='measurement'):
        c.advance(simulation_factory=lambda *a:pytest.fail('no world'),
            generators={'invent':lambda request:pytest.fail('no generation')},count=1,**kwargs)
    assert c.state['pending'] is None and not c.state['records']


def test_original_native_worlds_return_additional_loss_to_next_proposal_and_cold_campaign(tmp_path,fixed_corpus,monkeypatch):
    backend=Backend();instrument=contract(maximum_posts=144);observer=CommonContentObserver(tmp_path/'observer',instrument,backend=backend)
    c=campaign(tmp_path/'campaign',instrument);requests=[];worlds=[]
    def factory(spec,world_seed,run_id):
        worlds.append(run_id);seed()
        monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
        monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':c.binding['world']['source_commit']})
        return make_sim(tmp_path/'worlds'/run_id,native=NativeScienceKernel(spec))[0]
    def generate(request):
        requests.append(clone(request))
        return {'base_patch':None,'factors':[],'continuous':[],'provenance':PROVENANCE}
    first=c.advance(simulation_factory=factory,generators={'invent':generate},count=1,
        measurement_adapter=observer.measure,measurement_contract=instrument)
    assert first['observations'][0]['status']=='complete'
    value=first['observations'][0]['loss'];assert value<0
    c=campaign(tmp_path/'campaign',instrument)
    second=c.advance(simulation_factory=factory,generators={'invent':generate},count=1,
        measurement_adapter=observer.measure,measurement_contract=instrument)
    assert requests[1]['observations'][0]['observation']['loss']==value and len(requests[1]['history'])==1
    assert len(worlds)==2 and second['observations'][0]['status']=='complete'
    for record in (first,second):
        m=record['observations'][0]['metadata']['measurements'][0]
        assert m['measurement_adapter_contract_sha256']==digest(instrument)
        assert record['observations'][0]['loss']==-m['metrics']['native.common_content_utility_sum']['value']
        assert 'native.accepted_decisions' in m['metrics']
    assert campaign(tmp_path/'campaign',instrument).state==c.state
    assert observer.audit()['dispatch_intents']==len(backend.calls)
    c.state['records'][0]['observations'][0]['metadata']['measurements'][0]['measurement_adapter_contract_sha256']='changed-contract'
    c._save()
    with pytest.raises(ValueError,match='orchestration contract differs'):campaign(tmp_path/'campaign',instrument)


def test_unknown_critic_stops_the_actual_adaptive_batch_before_its_next_world(tmp_path,fixed_corpus,monkeypatch):
    backend=Backend([TimeoutError('SCRIPTED unresolved critic')]);instrument=contract(maximum_posts=144)
    observer=CommonContentObserver(tmp_path/'observer',instrument,backend=backend);c=campaign(tmp_path/'campaign',instrument);worlds=[]
    def factory(spec,world_seed,run_id):
        worlds.append(run_id);seed();monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
        monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':c.binding['world']['source_commit']})
        return make_sim(tmp_path/'worlds'/run_id,native=NativeScienceKernel(spec))[0]
    with pytest.raises(ObserverCompletionUnknown):
        c.advance(simulation_factory=factory,count=2,measurement_adapter=observer.measure,measurement_contract=instrument,
            generators={'invent':lambda r:{'base_patch':None,'factors':[],'continuous':[],'provenance':PROVENANCE}})
    assert len(worlds)==1 and len(backend.calls)==1
    assert not c.state['records'] and c.state['pending']['observations']==[]


def test_inert_declared_instrument_preserves_every_original_scientist_request(tmp_path,fixed_corpus,monkeypatch):
    monkeypatch.setattr('time.time',lambda:1234567890.)
    instrument={'schema':'SCRIPTED-inert-measurement.v1'};payloads=[];records=[]
    for label,declared in [('original',None),('inert',instrument)]:
        c=campaign(tmp_path/label/'campaign',declared,metric='native.accepted_decisions');calls=[]
        def factory(spec,world_seed,run_id):
            seed();monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
            monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':c.binding['world']['source_commit']})
            sim,raw=make_sim(tmp_path/label/'worlds'/run_id,native=NativeScienceKernel(spec));calls.append(raw);return sim
        options={} if declared is None else {'measurement_adapter':lambda sim,base:base,'measurement_contract':declared}
        record=c.advance(simulation_factory=factory,count=1,generators={
            'invent':lambda r:{'base_patch':None,'factors':[],'continuous':[],'provenance':PROVENANCE}},**options)
        payloads.append([payload for _,payload in calls[0]]);records.append(record)
    assert payloads[0] and payloads[0]==payloads[1]
    assert records[0]['observations'][0]['loss']==records[1]['observations'][0]['loss']
