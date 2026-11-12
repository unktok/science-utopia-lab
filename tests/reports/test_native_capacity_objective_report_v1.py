"""Scripted literal all-slot reports; not actual-Qwen institutional results."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_objective_instrument_loop_v1 as core
from scripts.reports import native_capacity_objective_loop_v1 as module
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_objective_instrument_report_v1 import evidence as old_evidence
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import clone,digest


def evidence(tmp_path,monkeypatch):
    p,a,old_records,old_traces=old_evidence(tmp_path,monkeypatch)
    def objective(name):return 'founder-activity' if name=='content-utility' else name
    p['schema']='scienceutopia.native-capacity-objective-loop.v1.plan';p['generations']=2
    p['objectives']=['throughput','founder-activity']
    p['measurement_contract']={'schema':'SCRIPTED-native-founder-boundaries','metric_id':'native.active_founder_boundary_sum'}
    p.pop('observer_contract')
    loss=json.loads((Path(__file__).resolve().parents[2]/'research/objectives/losses/native-active-founder-boundaries-v1.json').read_text())
    p['losses']={'throughput':p['losses']['throughput'],'founder-activity':loss}
    p['schedule']=[{'objective':objective(s['objective']),'generation':s['generation']}
                   for s in p['schedule'] if s['generation']<2];seal(p)
    records={(objective(o),g):clone(r) for (o,g),r in old_records.items() if g<2}
    traces={(objective(o),g):clone(r) for (o,g),r in old_traces.items() if g<2}
    used={v['suggestion']['suggestion_id'] for v in a['developer_references']['pairs']}
    used.update(o['suggestion_id'] for r in records.values() for o in r['observations'])
    a['worlds']=[w for w in a['worlds'] if w['identity'] in used]
    observations={v['suggestion']['suggestion_id']:v['observation'] for v in a['developer_references']['pairs']}
    observations.update({o['suggestion_id']:o for r in records.values() for o in r['observations']})
    for o in observations.values():
        for m in o['metadata']['measurements']:
            m['metrics'].pop('native.common_content_utility_sum')
            m['metrics']['native.active_founder_boundary_sum']={'status':'measured','value':15}
            m['measurement_adapter_contract_sha256']=digest(p['measurement_contract'])
    for w in a['worlds']:
        w['role']=w['role'].replace('search:content-utility','search:founder-activity')
        o=observations[w['identity']]
        w['scores']={k:evaluate_loss(v,o['metadata']['measurements'])['loss'] for k,v in p['losses'].items()}
        assigned='throughput' if w['role']=='developer-reference' else w['role'].split(':')[1]
        o['loss']=w['scores'][assigned]
    seal(a['developer_references'])
    authors=[]
    for slot in p['schedule']:
        key=slot['objective'],slot['generation'];r=records[key]
        r['request']['loss_spec']=clone(p['losses'][key[0]])
        r['request']['observations']=clone(a['developer_references']['pairs'])
        r['request']['developer_reference_context']['context_sha256']=a['developer_references']['content_sha256']
        r['request_sha256']=digest(r['request'])
        authors.append({**slot,'request_sha256':r['request_sha256'],'definition':r['definition'],
            'generation_error':r['generation_error'],'component_testing':traces[key]['component_testing']})
    selected={}
    for name in p['objectives']:
        pool=[o for (objective_name,g),r in records.items() if objective_name==name
              for o in r['observations'] if o['status']=='complete']
        best=min((o['loss'] for o in pool),default=None);ties=[o for o in pool if o['loss']==best]
        selected[name]={'loss':best,'all_tied_ids':[o['suggestion_id'] for o in ties],
            'selected_id':ties[0]['suggestion_id'] if ties else None,'system':ties[0]['candidate'] if ties else None,
            'completed_submissions':len(pool)}
    a.update(schema='scienceutopia.native-capacity-objective-loop-audit.v1',plan_sha256=p['content_sha256'],
        authoring=authors,selection={'selected':selected});seal(a)
    return p,a,records,traces


def test_all_four_slots_both_failure_types_and_actual_P_values_are_not_U(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch)
    report=core.summarize(p,a,records,traces,study='capacity-v1')
    assert report['schema']=='scienceutopia.native-capacity-objective-report.v1'
    assert report['score_order']==['throughput','founder-activity'] and len(report['slots'])==4
    assert report['slots'][0]['status']=='generation-failure' and report['slots'][1]['status']=='failed'
    groups,unavailable=core.cross_score_groups(report)
    assert len(groups)==1 and groups[0]['P']==-15 and 'U' not in groups[0]
    assert set(unavailable)=={'T0','P0'}
    with pytest.raises(ValueError):core.summarize(p,a,records,traces)  # never reinterpret as old T/U


@pytest.mark.parametrize('change',['slot','score','contract','selection'])
def test_changed_capacity_evidence_never_becomes_valid_report(tmp_path,monkeypatch,change):
    p,a,records,traces=evidence(tmp_path,monkeypatch)
    if change=='slot':records.pop(next(iter(records)))
    elif change=='score':a['worlds'][0]['scores']['founder-activity']=-999
    elif change=='contract':p['measurement_contract']['metric_id']='SCRIPTED-different';seal(p);a['plan_sha256']=p['content_sha256']
    else:a['selection']['selected']['founder-activity']['all_tied_ids']=[]
    seal(a)
    with pytest.raises(ValueError):core.summarize(p,a,records,traces,study='capacity-v1')


def test_actual_export_all_nulls_twice_keeps_literal_four_slots_and_seven_files(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch);root=tmp_path/'raw';root.mkdir()
    a['worlds']=[w for w in a['worlds'] if w['role']=='developer-reference']
    for name in p['objectives']:
        state=[]
        for g in range(2):
            r=records[name,g];r.update(definition=None,draws=[],observations=[],
                generation_error={'type':'ValueError','message':'SCRIPTED no terminal','loss':None})
            state.append(r);author=next(v for v in a['authoring'] if (v['objective'],v['generation'])==(name,g))
            directory=root/'search'/name/'authoring'/('generation-'+r['request_sha256']);directory.mkdir(parents=True)
            author.update(raw_directory=str(directory),definition=None,generation_error=clone(r['generation_error']),component_testing=None)
        core.save(root/'search'/name/'campaign/native-adaptive-state.json',{'pending':None,'records':state})
        a['selection']['selected'][name]={'loss':None,'all_tied_ids':[],'selected_id':None,'system':None,'completed_submissions':0}
    core.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    a['raw_inventory_sha256']=digest(_inventory(root));seal(a)
    audits=[tmp_path/'one.json',tmp_path/'two.json']
    for path in audits:core.save(path,{k:v for k,v in a.items() if k!='content_sha256'})
    outputs=[tmp_path/'out-one',tmp_path/'out-two'];before=_inventory(root)
    for out in outputs:module.export(SimpleNamespace(run=root,audit_one=audits[0],audit_two=audits[1],output=out))
    assert before==_inventory(root)
    assert len(list(outputs[0].iterdir()))==7
    assert {p.name:p.read_bytes() for p in outputs[0].iterdir()}=={p.name:p.read_bytes() for p in outputs[1].iterdir()}
