"""Best-known K versus best-own O; synthetic examples never change raw choices."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_optimization_incumbents_v1 as module
from scripts.run_native_parent_presentation_loop_v1 import ARM_ORDER
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import digest
from utopia.system.native_planning_controls import ORDER


def seal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def fixture(*,throughput=(-4.,None,-6.),utility=(-9.,-8.,-10.)):
    refs=[{'label':name,'physical_job':'reference-'+name,
        'scores':{'throughput':-10. if i==1 else -5.,'content-utility':-8. if i==6 else -3.}}
        for i,name in enumerate(ORDER)]
    slots=[];selected={}
    for objective,values in [('throughput',throughput),('content-utility',utility)]:
        for g,loss in enumerate(values):
            slots.append({'objective':objective,'generation':g,'status':'complete' if loss is not None else 'failed',
                'physical_job':'SCRIPTED-'+objective+'-'+str(g),'loss':loss,
                'cross_scores':{'throughput':loss if objective=='throughput' else -4. if loss is not None else None,
                    'content-utility':loss if objective=='content-utility' else -3. if loss is not None else None}})
        good=[r for r in slots if r['objective']==objective and r['status']=='complete']
        best=min((r['loss'] for r in good),default=None);ties=[r['physical_job'] for r in good if r['loss']==best]
        selected[objective]={'loss':best,'selected_id':ties[0] if ties else None,'all_tied_ids':ties,'completed_submissions':len(good)}
    return seal({'schema':'scienceutopia.native-planning-objective-report.v1','source_commit':'a'*40,
        'plan_sha256':'b'*64,'audit_sha256':'c'*64,'score_order':['throughput','content-utility'],
        'references':refs,'slots':slots,'frozen_selection':selected,'SCRIPTED':'synthetic scalar report fixture'})


def variant(scope):
    p=fixture()
    if scope=='planning':return p
    if scope=='presentation':
        p['schema']='scienceutopia.native-parent-presentation-report.v1';p['arm_order']=list(ARM_ORDER)
        p['arms']={key:{'objective':key.rsplit('-',1)[0],'presentation':key.rsplit('-',1)[1]} for key in ARM_ORDER}
        slots=[];selections={}
        for key in ARM_ORDER:
            objective=p['arms'][key]['objective'];rows=deepcopy([r for r in p['slots'] if r['objective']==objective])
            for r in rows:r.update(arm=key,presentation=p['arms'][key]['presentation'],physical_job=r['physical_job']+'-'+key)
            slots+=rows;selected=deepcopy(p['frozen_selection'][objective])
            selected['selected_id']+='-'+key
            selected['all_tied_ids']=[v+'-'+key for v in selected['all_tied_ids']];selections[key]=selected
        p['slots']=slots;p['frozen_selection']=selections;return seal(p)
    p['schema']='scienceutopia.native-parameter-comparator-report.v1';p['objectives']=p.pop('score_order')
    p['references']=[{'identity':r['physical_job'],'scores':r['scores'],'system_sha256':'f'*64} for r in p['references']]
    rows=[{'method':method,'objective':r['objective'],'generation':r['generation'],'identity':r['physical_job'],
        'status':r['status'],'assigned_loss':r['loss'],'scores':r['cross_scores'],'reserve_units':20}
        for method in ('prior-free-program','numeric-reserve') for r in p['slots']]
    p['slots']=rows;p['new_numeric_slots']=p['reused_free_slots']=6;p['held_out_evaluation']=False
    selected=p.pop('frozen_selection');p['anchors']={}
    for objective in p['objectives']:
        ref=min(p['references'],key=lambda r:r['scores'][objective])
        p['anchors'][objective]={'identity':ref['identity'],'loss':ref['scores'][objective]}
        selected[objective].update(system={'SCRIPTED':'not an executable program'},reference_loss=ref['scores'][objective])
    p['numeric_selection']=seal({'plan_sha256':p['plan_sha256'],'selected':selected,'baseline_fallback':False,'held_out_evaluation':False})
    return seal(p)


@pytest.mark.parametrize('scope',['planning','presentation','numeric'])
def test_reference_incumbent_and_strict_own_improvement_are_separate_and_leave_input_unchanged(scope):
    p=variant(scope);before=deepcopy(p);r=module.summarize(p)
    assert p==before and not r['interpretation']['original_selection_changed']
    assert len(r['histories'])==(4 if scope=='presentation' else 2)
    for h in r['histories']:
        assert [x['generation'] for x in h['path']]==[-1,0,1,2]
        assert [x['consumed_slots'] for x in h['path']]==[0,1,2,3]
        assert h['path'][0]['best_own']['loss'] is None and h['path'][0]['completed_own']==0
        if h['objective']=='throughput':
            assert h['final']['best_known']['loss']==-10. and h['final']['best_known']['origin']=='reference'
            assert h['final']['best_own']['loss']==-6. and h['final']['own_improvement_over_reference']==-4.
            assert h['final']['known_improvement_over_reference']==0
            assert h['path'][2]['slot_status']=='failed' and h['path'][2]['completed_own']==1
        else:
            assert [x['best_known']['loss'] for x in h['path']]==[-8.,-9.,-9.,-10.]
            assert h['final']['best_known']['origin']=='own' and h['final']['known_improvement_over_reference']==2.
    assert r['reused_prior_free_slots_are_not_new_histories']==(6 if scope=='numeric' else 0)


def test_reference_first_ties_keep_all_ids_and_all_failed_own_pool_stays_missing():
    p=fixture(throughput=(-10.,-10.,None),utility=(None,None,None));r=module.summarize(p)
    t,u=r['histories']
    assert t['final']['best_known']['identity']=='reference-advice-reserve21-all'
    assert t['final']['best_known']['all_tied_ids']==['reference-advice-reserve21-all','SCRIPTED-throughput-0','SCRIPTED-throughput-1']
    assert t['final']['best_own']['identity']=='SCRIPTED-throughput-0'
    assert u['final']['best_known']['loss']==-8. and u['final']['best_own']['loss'] is None
    assert u['original_own_selection']['selected_id'] is None and u['final']['completed_own']==0


@pytest.mark.parametrize('change',['reference-order','missing-reference','bool','null-penalty','wrong-objective',
    'duplicate-generation','duplicate-identity','selection','ties','source','criterion','reference-as-own'])
def test_malformed_or_reselected_inputs_are_not_repaired(change):
    p=fixture()
    if change=='reference-order':p['references'].reverse()
    elif change=='missing-reference':p['references'].pop()
    elif change=='bool':p['slots'][0]['loss']=True
    elif change=='null-penalty':p['slots'][1]['loss']=0.
    elif change=='wrong-objective':p['slots'][0]['objective']='other'
    elif change=='duplicate-generation':p['slots'][1]['generation']=0
    elif change=='duplicate-identity':p['slots'][2]['physical_job']=p['slots'][0]['physical_job']
    elif change=='selection':p['frozen_selection']['throughput']['selected_id']='reference-advice-reserve21-all'
    elif change=='ties':p['frozen_selection']['content-utility']['all_tied_ids']=[]
    elif change=='source':p['source_commit']='unknown'
    elif change=='criterion':p['slots'][0]['cross_scores']['throughput']=-999.
    else:p['slots'][0]['physical_job']='reference-cut-reserve21-all'
    seal(p)
    with pytest.raises(ValueError):module.summarize(p)


def test_numeric_wrong_warm_start_or_partial_original_selection_rejected():
    p=variant('numeric');p['anchors']['throughput']['loss']=-11.;seal(p)
    with pytest.raises(ValueError,match='warm-start'):module.summarize(p)
    p=variant('numeric');p['numeric_selection']['baseline_fallback']=True;seal(p['numeric_selection']);seal(p)
    with pytest.raises(ValueError,match='own-only'):module.summarize(p)


def test_two_export_calls_inputs_are_read_only_and_qa_plot_keeps_nulls(tmp_path,monkeypatch):
    p=fixture(throughput=(-10.,-10.,None),utility=(None,None,None));inputs=[tmp_path/'input-one/report.json',tmp_path/'input-two/report.json']
    for path in inputs:save(path,{k:v for k,v in p.items() if k!='content_sha256'})
    before=[v.read_bytes() for v in inputs];monkeypatch.setattr(module,'pinned_revision',lambda root:'d'*40)
    outs=[tmp_path/'out-one',tmp_path/'out-two']
    for out in outs:module.export(SimpleNamespace(report_one=inputs[0],report_two=inputs[1],output=out,software_qa=True))
    assert [v.read_bytes() for v in inputs]==before
    assert {v.name:v.read_bytes() for v in outs[0].iterdir()}=={v.name:v.read_bytes() for v in outs[1].iterdir()}
    assert len(list(outs[0].iterdir()))==5 and len((outs[0]/'paths.csv').read_text().splitlines())==9
    assert 'SCRIPTED SOFTWARE QA' in (outs[0]/'optimization-incumbents.svg').read_text()
    out=checked(json.loads((outs[0]/'report.json').read_text()))
    assert out['software_qa_plot'] and out['analysis_source_commit']=='d'*40
    with pytest.raises(ValueError):module.export(SimpleNamespace(report_one=inputs[0],report_two=inputs[0],output=tmp_path/'bad'))


def test_actual_closed_planning_readout_has_zero_generated_gain_without_an_extra_native_world():
    root=Path(__file__).resolve().parents[2];original=checked(json.loads((root/'research/data/native-planning-objective-loop-v1/report.json').read_text()))
    report=module.summarize(original)
    for h in report['histories']:
        final=h['final'];assert final['best_known']['loss']==final['best_own']['loss']
        assert final['best_known']['origin']=='reference' and final['own_improvement_over_reference']==0
    assert report['interpretation']['new_model_calls']==report['interpretation']['new_native_worlds']==0


def test_presentation_condition_colors_do_not_reverse_with_balanced_arm_order(tmp_path,monkeypatch):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    captured=[];original=plt.subplots
    def subplots(*a,**kw):
        fig,axes=original(*a,**kw);captured.extend(axes);return fig,axes
    monkeypatch.setattr(plt,'subplots',subplots)
    module.render(module.summarize(variant('presentation')),tmp_path,software_qa=True)
    for ax in captured:
        for line in ax.lines:
            if 'literal' in line.get_label():assert line.get_color()=='#b47835'
            if 'control' in line.get_label():assert line.get_color()=='#087f8c'
