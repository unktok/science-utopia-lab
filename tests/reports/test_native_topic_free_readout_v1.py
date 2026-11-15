"""Pure SCRIPTED arithmetic/slot projections; not native or model evidence."""
import pytest

from scripts.reports import native_topic_free_readout_v1 as reader
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.blackbox import Observation
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.optimization.native_topic_objectives_v1 import objective_specs,OBJECTIVES
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


def fixture(*,null=None):
    anchor=SystemSpec('scripted-readout-not-a-native-world',1).to_dict()
    systems={label:{**clone(anchor),'metadata':{'SCRIPTED':label}} for label in ('core-only','core-plus-related')}
    losses=objective_specs({'throughput':loss_spec(),
        'content-utility':loss_spec('native.common_content_utility_sum')})
    p={'schema':'scienceutopia.native-topic-free-optimization.v1.plan','source_commit':'a'*40,
       'objectives':list(OBJECTIVES),'generations':2,
       'design_space':{'world_law_scope':'fixed-native-effects-institution-workflow-v6'},
       'initial_system':anchor,'losses':losses,'reference_order':list(systems),
       'reference_systems':systems,'optimizer_reference_labels':list(systems),
       'schedule':[{'objective':o,'generation':g} for g in range(2)
                   for o in (OBJECTIVES if g==0 else OBJECTIVES[::-1])]}
    p['content_sha256']=digest(p)
    worlds=[]; observations={}; records={}
    def add(identity,spec,objective,role,g=0,failed=False):
        metrics={key:{'status':'measured','value':value} for key,value in (
            ('native.accepted_decisions',12+g),('native.common_content_utility_sum',7+g),
            (reader.METRIC,100-10*g),(reader.UNCOLLECTED_METRIC,0))}
        measurements=[] if failed else [{'run_id':identity,'system_fingerprint':SystemSpec.from_dict(spec).fingerprint,
            'metrics':metrics,'native_workflow_interval':{'institutional_work_events':g}}]
        evaluated={k:evaluate_loss(v,measurements) for k,v in losses.items()}
        o=Observation('observation-'+identity,identity,spec,'failed' if failed else 'complete',
            evaluated[objective]['loss'],{'measurements':measurements,
            'technical_failures':[{'SCRIPTED':'retained technical null'}] if failed else [],
            'loss_spec_sha256':loss_spec_sha256(losses[objective]),'loss_evaluation':evaluated[objective],
            'system_fingerprint':SystemSpec.from_dict(spec).fingerprint}).to_dict()
        observations[identity]=o
        worlds.append({'identity':identity,'role':role,'objective':objective,'status':o['status'],
                       'system':spec,'scores':{k:v['loss'] for k,v in evaluated.items()}})
        return o
    for label,spec in systems.items(): add('workflow-reference-'+label,spec,'throughput','developer-reference')
    for slot in p['schedule']:
        objective,g=slot['objective'],slot['generation']; key=(objective,g)
        identity='SCRIPTED-'+objective+'-'+str(g)
        spec={**clone(anchor),'metadata':{'SCRIPTED':identity}}
        req={'generation':g,'loss_spec':losses[objective],
             'parent_system':systems['core-only'],'based_on_observation_id':'SCRIPTED-reference'}
        missing=null=='generation' and key==('throughput',0)
        o=None if missing else add(identity,spec,objective,'workflow-own-proposal',g,
                                  failed=null=='runtime' and key==('throughput',0))
        records[key]={'request':req,'request_sha256':digest(req),
                      'generation_error':{'SCRIPTED':'missing submission, not a zero'} if missing else None,
                      'draws':[] if missing else [{'suggestion':{'candidate':spec}}],
                      'observations':[] if missing else [o]}
    selected={}
    for objective in OBJECTIVES:
        pool=[o for (obj,g),r in records.items() if obj==objective for o in r['observations'] if o['status']=='complete']
        best=min(o['loss'] for o in pool); ties=[o for o in pool if o['loss']==best]
        selected[objective]={'loss':best,'all_tied_ids':[o['suggestion_id'] for o in ties],
                             'selected_id':ties[0]['suggestion_id'],'system':ties[0]['candidate']}
    a={'schema':'scienceutopia.native-topic-free-optimization.v1.audit','source_commit':p['source_commit'],
       'plan_sha256':p['content_sha256'],'closure':{'terminal':{'status':'closed'}},
       'source_proof':{'status':'verified-exact-source-closure','SCRIPTED':True},
       'new_model_calls':0,'new_code_executions':0,'held_out_evaluation':False,
       'worlds':worlds,'selection':{'selected':selected,'baseline_fallback':False}}
    a['content_sha256']=digest(a)
    return p,a,records,observations


def test_all_three_histories_and_literal_resource_input_remain_present():
    p,a,r,o=fixture(); result=reader.analyze(p,a,r,o)
    assert result['score_order']==list(OBJECTIVES) and result['consumed_own_slots']==6
    assert result['physical_worlds']==8 and len(result['slots'])==6
    for objective in OBJECTIVES:
        path=result['loss_paths'][objective]
        assert [x['generation'] for x in path]==[0,1]
        assert path[1]['best_own_loss']<path[0]['best_own_loss']
    assert [x['metrics'][reader.METRIC]['value'] for x in result['slots']]==[100,100,100,90,90,90]
    assert all(x['literal_system_changed'] for x in result['slots'])
    assert not result['interpretation']['structural_change_is_effect']
    assert not result['interpretation']['independent_optimizer_replications']
    assert not result['interpretation']['publication_ready']


@pytest.mark.parametrize('kind',['generation','runtime'])
def test_null_slots_and_unknown_resource_cost_are_not_filtered_or_imputed(kind):
    p,a,r,o=fixture(null=kind); result=reader.analyze(p,a,r,o)
    first=result['slots'][0]
    assert len(result['slots'])==6 and first['loss'] is None
    assert first['status']==('generation-null' if kind=='generation' else 'failed')
    assert first['metrics'][reader.METRIC]['value'] is None
    assert first['metrics'][reader.METRIC]['status']=='measurement-not-recorded'
    path=result['loss_paths']['throughput']
    assert path[0]['best_own_loss'] is None and path[0]['best_known_loss_including_visible_references']==-12
    assert first['physical_job'] is None if kind=='generation' else first['physical_job'] is not None


def test_original_selection_or_loss_is_never_silently_recomputed_into_a_new_winner():
    p,a,r,o=fixture(); changed=clone(a)
    changed['selection']['selected']['throughput']['selected_id']='workflow-reference-core-only'
    with pytest.raises(ValueError,match='own-only selection'):
        reader.analyze(p,changed,r,o)
    changed=clone(o); changed[next(iter(changed))]['loss']=-999
    with pytest.raises(ValueError,match='literal original outcome'):
        reader.analyze(p,a,r,changed)


def sealed(value):
    return {**value,'content_sha256':digest(value)}


def session_fixture():
    record={'request_sha256':'SCRIPTED-request','definition':{'SCRIPTED':'not a native program'},
            'generation_error':None,'draws':[]}
    response=sealed({'request_sha256':record['request_sha256'],'status':'generated',
        'definition':record['definition'],'component_testing':{'probe_attempts':0,'returned':0,'raised':0,
            'new_native_worlds':0,'new_model_calls_from_tests':0,'veto_on_finish':False}})
    return record,{'request_sha256':record['request_sha256'],'definition':record['definition'],
                   'response':response,'steps':[]}


def test_complete_original_component_summary_reconciles_with_full_prefix():
    record,session=session_fixture(); result=reader.construction(record,session)
    assert not result['terminal_response_missing'] and result['recorded_completed_steps']==0
    assert result['component_testing']['probe_attempts']==0
    session['response']['component_testing']['probe_attempts']=1
    session['response']=sealed({k:v for k,v in session['response'].items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='component totals differ'):
        reader.construction(record,session)


def test_missing_terminal_preserves_prefix_without_fabricating_final_summary():
    record,session=session_fixture(); record['generation_error']={'SCRIPTED':'retained original failure'}
    session['response']=None
    session['steps']=[sealed({'step':0,'status':'rejected','transition':None})]
    result=reader.construction(record,session)
    assert result['terminal_response_missing'] and result['recorded_completed_steps']==1
    assert result['component_testing'] is None and result['events'] is None
    assert not result['charged_model_calls_inferred_from_steps']
    session['steps']=[sealed({'step':1,'status':'rejected','transition':None})]
    with pytest.raises(ValueError,match='chronological completed step prefix'):
        reader.construction(record,session)


def test_a_reader_never_adopts_reference_fallback_or_relabels_held_out_evidence():
    p,a,r,o=fixture(); a['selection']['baseline_fallback']=True
    with pytest.raises(ValueError,match='exact normally closed'):
        reader.analyze(p,a,r,o)


def test_opt_in_literal_projection_of_retained_public_software_run():
    """Read existing small journals only; no models, Docker, render or cold rerun."""
    import json
    import os
    from pathlib import Path
    location=os.environ.get('SCIENCE_UTOPIA_RETAINED_TOPIC_FREE_FIXTURE')
    if not location: pytest.skip('optional existing complete SCRIPTED public-path fixture')
    parent=Path(location).resolve(); root=parent/'free-study'
    load=lambda p:reader.checked(json.loads(p.read_text()))
    plan,audit=load(root/'plan.json'),load(parent/'audit-retained.json')
    records={}; observations={}; traces=[]
    for label in plan['reference_order']:
        o=load(root/'references'/label/'observation.json'); observations[o['suggestion_id']]=o
    for objective in OBJECTIVES:
        state=json.loads((root/'search'/objective/'campaign/native-adaptive-state.json').read_text())
        for g,r in enumerate(state['records']):
            records[objective,g]=r
            for o in r['observations']:
                if o is not None: observations[o['suggestion_id']]=o
            outer=root/'search'/objective/'authoring'/('proposal-'+r['request_sha256'])
            wrapper=load(outer/'result.json')
            inner=outer/'editor-session/authoring'/('generation-'+r['request_sha256'])
            traces.append(reader.construction(r,{'request_sha256':r['request_sha256'],
                'definition':wrapper['definition'],'response':load(inner/'response.json'),
                'steps':[load(p) for p in sorted(inner.glob('step-*.completed.json'))]}))
    result=reader.analyze(plan,audit,records,observations)
    assert result['physical_worlds']==8 and len(result['slots'])==6
    assert all(row['status']=='complete' and row['institutional_work_events']==4 for row in result['slots'])
    assert len(traces)==6 and sum(t['recorded_completed_steps'] for t in traces)==42
    assert all(not t['terminal_response_missing'] for t in traces)


def test_finite_continuation_uses_exact_new_scope_and_original_decoders(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from scripts import finish_native_topic_free_readouts_v1 as chain
    observed={}
    def capture(args,**kwargs): observed.update(kwargs); return 'SCRIPTED-call-not-waiting'
    monkeypatch.setattr(chain,'finish',capture)
    assert chain.run(SimpleNamespace(frozen_source=tmp_path))=='SCRIPTED-call-not-waiting'
    assert observed=={'plan_schema':'scienceutopia.native-topic-free-optimization.v1.plan',
        'preceding_schema':'scienceutopia.native-topic-free-optimization.v1.finish',
        'continuation_schema':'scienceutopia.native-topic-free-readout.v1.finish',
        'report_module':'scripts.reports.native_topic_free_readout_v1',
        'report_extra_arguments':('--frozen-source',str(tmp_path.resolve()))}
