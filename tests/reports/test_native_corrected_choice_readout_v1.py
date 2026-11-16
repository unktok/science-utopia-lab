"""All24 SCRIPTED slots/selection semantics, not native result estimates."""
from copy import deepcopy
import pytest

from scripts import run_native_corrected_choice_search_v1 as driver
from scripts.reports import native_priority_method_readout_v1 as reader
from tests.reports.test_native_priority_method_readout_v1 import fixture as legacy_fixture
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest


def seal(value):
    value={k:deepcopy(v) for k,v in value.items() if k!='content_sha256'}
    return {**value,'content_sha256':digest(value)}


def fixture(*,delta=-1.,null_free=False):
    old,a,oldslots,refs=legacy_fixture();p=deepcopy(old)
    order=[(m,0,o) for o in reader.OBJECTIVES for m in reader.METHODS]
    p.update(schema=driver.SCHEMA+'.plan',protocol=driver.PROTOCOL,replication_seeds=[79011],generations=4,
        numeric_kernels={reader.METHODS[0]:'SCRIPTED uniform',reader.METHODS[1]:'SCRIPTED initial choices'},
        schedule=[{'method':m,'replication':h,'objective':o,'generation':g}
            for g in range(4) for m,h,o in (order if g%2==0 else order[::-1])])
    p=seal(p);lookup={};worlds=deepcopy(a['worlds'][:3])
    for entry in oldslots:
        e=deepcopy(entry);s=e['slot'];g=s['generation']+2*s['replication'];s.update(generation=g,replication=0)
        identity='shared-id-g'+str(g);o=e['observation'];o.update(suggestion_id=identity,observation_id='observation-'+identity)
        e['suggestion']['suggestion_id']=identity
        values={'throughput':-10.,reader.OBJECTIVES[0]:-10.+delta,reader.OBJECTIVES[1]:-9.+delta}
        for measurement in o['metadata']['measurements']:
            measurement['run_id']='SCRIPTED-'+identity
            for key,value in values.items():measurement['metrics'][key]['value']=value
        scores={key:evaluate_loss(spec,o['metadata']['measurements']) for key,spec in p['losses'].items()}
        o['loss']=scores[s['objective']]['loss'];o['metadata']['loss_evaluation']=scores[s['objective']]
        key=(*reader.history_key(s),g)
        if null_free and s['method']==reader.METHODS[2] and s['objective']==reader.OBJECTIVES[0]:
            e.update(suggestion=None,observation=None,generation_error={'SCRIPTED':'known no-submission'})
        else:
            worlds.append({'identity':identity,'role':'workflow-own-proposal' if s['method']==reader.METHODS[2] else 'numeric-own-proposal',
                'system':deepcopy(o['candidate']),'status':'complete','method':s['method'],'optimizer_history':0,
                'objective':s['objective'],'scores':{k:v['loss'] for k,v in scores.items()}})
        lookup[key]=e
    slots=[lookup[(*reader.history_key(s),s['generation'])] for s in p['schedule']]
    primary,secondary=({m:{'0':{}} for m in reader.METHODS} for _ in range(2))
    for method in reader.METHODS:
        for objective in reader.OBJECTIVES:
            own=[e['observation'] for e in slots if reader.history_key(e['slot'])==(method,0,objective) and e['observation'] is not None]
            references=[]
            for label in p['optimizer_reference_labels']:
                reference=deepcopy(refs[label]);reference['loss']=evaluate_loss(p['losses'][objective],reference['metadata']['measurements'])['loss'];references.append(reference)
            reference_loss=min(o['loss'] for o in references)
            kwargs={'reference_loss':reference_loss,'complete_own':len(own)}
            secondary[method]['0'][objective]=driver.endpoint([('own',o) for o in own],**kwargs)
            primary[method]['0'][objective]=driver.endpoint([('reference',o) for o in references]+[('own',o) for o in own],**kwargs)
    selection=seal({'selected':primary,'own_only_selected':secondary,'baseline_fallback':False,
        'held_out_evaluation':False,'primary_is_measured_best_known_not_own_discovery':True})
    a.update(schema=driver.AUDIT_SCHEMA,plan_sha256=p['content_sha256'],worlds=worlds,selection=selection)
    a['closure']['terminal']['observations']=len(worlds)
    return p,seal(a),slots,refs


@pytest.mark.parametrize('delta,origin',[(-1.,'own'),(0.,'reference'),(1.,'reference')])
def test_corrected_four_step_paths_and_both_endpoints_keep_all24_slots(delta,origin):
    p,a,slots,refs=fixture(delta=delta);report=reader.analyze(p,a,slots,refs)
    assert report['schema']==reader.CORRECTED_SCHEMA and len(report['slots'])==24
    assert len(report['selected'])==len(report['own_only_selected'])==len(report['paths'])==6
    assert all(len(path)==4 for path in report['paths'].values())
    assert all(r['selected_origin']==origin for r in report['selected'])
    assert all(r['suggestion_id']=='shared-id-g0' for r in report['own_only_selected'])
    assert report['coverage']['physical_worlds']==27
    assert not report['method_superiority_claimed'] and not report['publication_ready']
    if origin=='reference':assert all(r['cell_id'] is None and r['returned_minus_reference']==0 for r in report['selected'])


def test_no_submissions_keep_own_endpoint_absent_while_measured_warm_parent_stays_labeled():
    p,a,slots,refs=fixture(null_free=True);report=reader.analyze(p,a,slots,refs)
    assert report['coverage']['generation_nulls']==4 and report['coverage']['physical_worlds']==23
    own=next(r for r in report['own_only_selected'] if r['method']==reader.METHODS[2] and r['objective']==reader.OBJECTIVES[0])
    primary=next(r for r in report['selected'] if r['method']==reader.METHODS[2] and r['objective']==reader.OBJECTIVES[0])
    assert own['loss'] is own['cell_id'] is own['suggestion_id'] is None
    assert primary['selected_origin']=='reference' and primary['cell_id'] is None and primary['loss']==-10.


@pytest.mark.parametrize('problem',['origin','own-label','profile','generation','extra-world','partial'])
def test_old_profile_or_relabelled_reference_cannot_satisfy_new_scientific_readout(problem):
    p,a,slots,refs=fixture(delta=1.)
    if problem=='origin':a['selection']['selected'][reader.METHODS[0]]['0'][reader.OBJECTIVES[0]]['selected_origin']='own'
    elif problem=='own-label':a['selection']['own_only_selected'][reader.METHODS[0]]['0'][reader.OBJECTIVES[0]]['selected_id']='workflow-reference-zero'
    elif problem=='profile':p['protocol']='old-profile'
    elif problem=='generation':p['generations']=2
    elif problem=='extra-world':a['worlds'].append(deepcopy(a['worlds'][3]))
    else:slots.pop()
    p=seal(p);a['plan_sha256']=p['content_sha256'];a=seal(a)
    with pytest.raises(ValueError):reader.analyze(p,a,slots,refs)


def test_generation_three_collect_reads_its_actual_generation_two_parent_not_generation_zero(tmp_path):
    key=(reader.METHODS[1],0,reader.OBJECTIVES[0]);directory=tmp_path/'search'/key[0]/'history-0'/key[2]
    parent={'SCRIPTED':'actual generation2 measured parent'}
    reader.save(directory/'generation-2/optimizer-after-tell.json',{'optimizer':{'observations':[{
        'observation_id':'SCRIPTED-observation-g2','candidate':parent}]},'space_binding':{'anchor':{'SCRIPTED':'anchor'}}})
    reader.save(directory/'generation-0/optimizer-after-tell.json',{'optimizer':{'observations':[]}})
    suggestion={'suggestion_id':'SCRIPTED-g3','based_on_observation_id':'SCRIPTED-observation-g2','candidate':{'SCRIPTED':'new'}}
    reader.save(directory/'generation-3/started.json',{'suggestion':suggestion})
    reader.save(directory/'generation-3/observation.json',{'SCRIPTED':'not an actual native observation'})
    slots,refs=reader.collect(tmp_path,{'reference_order':[],'schedule':[{
        'method':key[0],'replication':0,'objective':key[2],'generation':3}]})
    assert slots[0]['parent_system']==parent and not refs
