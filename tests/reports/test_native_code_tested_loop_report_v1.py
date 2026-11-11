"""All-slot and actual feedback aggregation, without new native/model execution."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_code_tested_loop_v1 as module
from tests.reports.test_native_code_tested_loop_v1 import plan
from tests.optimization.test_native_post_edit_feedback_v1 import fixture as editor_fixture
from tests.optimization.test_native_post_edit_feedback_v1 import source_action,finish,directory,BAD,GOOD
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone,digest


def seal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def evidence(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);worlds=[];records={};traces={};authors=[]
    def world(identity,role,system,failed=False):
        metrics={k:{'value':v,'status':'measured'} for k,v in {
            'native.accepted_decisions':2,'native.accepted_peer_score_sum':7.,'native.review_records':3}.items()}
        measurement={'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':metrics,
            'run_id':identity,'system_fingerprint':digest(system)}
        scores={k:evaluate_loss(v,[] if failed else [measurement])['loss'] for k,v in p['losses'].items()}
        value={'identity':identity,'role':role,'seed':61001,'status':'failed' if failed else 'complete',
            'system':clone(system),'scores':scores,'physical_proof':{'measurement':measurement}}
        worlds.append(value);return value
    for label in p['reference_order']:world('reference-'+label,'developer-reference',p['reference_systems'][label])
    summary={'probe_attempts':0,'returned':0,'raised':0,'new_native_worlds':0,
        'new_model_calls_from_tests':0,'veto_on_finish':False}
    for i,slot in enumerate(p['schedule']):
        arm,g=slot['arm'],slot['generation'];objective=p['assignments'][arm]['objective']
        request={'generation':g,'loss_spec':clone(p['losses'][objective]),'history':[] if g==0 else [{'SCRIPTED':'own-prior'}]}
        definition={'SCRIPTED':'literal-'+str(i)};identity='SCRIPTED-world-'+str(i)
        w=world(identity,'search:'+arm,p['campaign_bindings']['run-00'][arm]['initial_system'],failed=i==0)
        records[arm,g]={'request':request,'request_sha256':digest(request),'definition':definition,
            'draws':[{'suggestion':{'candidate':clone(w['system'])}}],
            'generation_error':None,'observations':[{'suggestion_id':identity,'candidate':clone(w['system']),
                'status':w['status'],'loss':w['scores'][objective]}]}
        traces[arm,g]={'component_testing':clone(summary),'completed_steps':0,'events':[],
            'same_fixture_later_code_comparisons':[],'automatic_repair_claimed':False,
            'drawn_candidate_artifact_observations':None}
        authors.append({**slot,'request_sha256':digest(request),'definition':definition,
            'generation_error':None,'component_testing':clone(summary)})
    selected={}
    for arm in p['arm_order']:
        rows=[records[arm,g]['observations'][0] for g in (0,1)]
        rows=[r for r in rows if r['status']=='complete'];loss=min(r['loss'] for r in rows)
        tied=[r for r in rows if r['loss']==loss]
        selected[arm]={'loss':loss,'all_tied_ids':[r['suggestion_id'] for r in tied],
            'selected_id':tied[0]['suggestion_id'],'system':clone(tied[0]['candidate']),'completed_submissions':len(rows)}
    a=seal({'schema':'scienceutopia.native-code-tested-loop-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'closure':{'terminal':{'status':'closed'}},
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,
        'new_code_executions':0,'held_out_evaluation':False,'worlds':worlds,'authoring':authors,
        'selection':{'selected':selected}})
    return p,a,records,traces


def test_identifier_join_preserves_all_four_slots_nulls_ties_and_both_scores(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch)
    a['worlds'].reverse();a['authoring'].reverse();seal(a)
    r=module.summarize(p,a,dict(reversed(list(records.items()))),traces)
    assert [(x['arm'],x['generation']) for x in r['slots']]==[(s['arm'],s['generation']) for s in p['schedule']]
    assert r['slots'][0]['status']=='failed' and r['slots'][0]['loss'] is None
    assert all(v is None for v in r['slots'][0]['cross_scores'].values())
    assert len(r['physical_worlds'])==7 and len(r['references'])==3
    assert len(r['frozen_selection']['efficiency:code-and-graph']['all_tied_ids'])==2
    assert not r['interpretation']['held_out_evaluation'] and not r['interpretation']['feedback_superiority_demonstrated']


@pytest.mark.parametrize('change',['stopped','source','slot-missing','duplicate-world','score',
    'literal-request','definition','selection','missing-tie','probe-total','extra-world'])
def test_rejects_inconsistent_evidence_without_fallback(tmp_path,monkeypatch,change):
    p,a,records,traces=evidence(tmp_path,monkeypatch);key=next(iter(records))
    if change=='stopped':a['closure']['terminal']['status']='stopped'
    elif change=='source':a['source_commit']='0'*40
    elif change=='slot-missing':records.pop(key)
    elif change=='duplicate-world':a['worlds'].append(clone(a['worlds'][0]))
    elif change=='score':a['worlds'][0]['scores']['efficiency']+=1
    elif change=='literal-request':records[key]['request']['history'].append({'SCRIPTED':'changed'})
    elif change=='definition':records[key]['definition']={'SCRIPTED':'repaired'}
    elif change=='selection':a['selection']['selected']['efficiency:code-and-graph']['selected_id']='invented'
    elif change=='missing-tie':a['selection']['selected']['efficiency:code-and-graph']['all_tied_ids'].pop()
    elif change=='probe-total':traces[key]['component_testing']['returned']=99
    else:
        extra=clone(a['worlds'][0]);extra['identity']='unaccounted';a['worlds'].append(extra)
    seal(a)
    with pytest.raises(ValueError):module.summarize(p,a,records,traces)


def test_failed_only_arm_keeps_no_policy_not_reference_fallback(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch);arm=p['arm_order'][0]
    for g in (0,1):
        o=records[arm,g]['observations'][0];o.update(status='failed',loss=None)
        w=next(w for w in a['worlds'] if w['identity']==o['suggestion_id'])
        w.update(status='failed',scores={k:None for k in p['losses']})
    a['selection']['selected'][arm]={'loss':None,'all_tied_ids':[],'selected_id':None,'system':None,'completed_submissions':0};seal(a)
    r=module.summarize(p,a,records,traces)
    assert r['frozen_selection'][arm]['selected_id'] is None
    assert r['frozen_selection'][arm]['loss'] is None


def test_actual_step_format_tracks_same_fixture_later_code_without_causal_repair_claim(tmp_path):
    gen,model,body,calls=editor_fixture(tmp_path,[source_action(BAD),source_action(GOOD),finish()])
    gen(body);d=directory(tmp_path)
    steps=[json.loads(p.read_text()) for p in sorted(d.glob('step-*.completed.json'))]
    response=json.loads((d/'response.json').read_text())
    r=module.component_trace(steps,response)
    assert len(r['same_fixture_later_code_comparisons'])==4
    assert all(c['transition']=='raised-to-returned' for c in r['same_fixture_later_code_comparisons'])
    assert len(calls)==8 and not r['automatic_repair_claimed']
    assert r['drawn_candidate_artifact_observations'] is None
    steps[1]['transition']['result']['component_feedback']['probe_offset']=0
    with pytest.raises(ValueError,match='prefix'):module.component_trace(steps,response)


def test_recorded_actual_closed_first_authoring_summary_does_not_run_code_or_model():
    root=Path('/Users/shiro/unktok/dev/science-utopia-lab-experiments/native-code-tested-loop-v1-a1/outputs/native-code-tested-loop-v1-a1')
    dirs=[d for d in (root/'search/run-00/throughput--code-and-graph/authoring').glob('generation-*/authoring/generation-*')
        if (d/'request.json').is_file() and json.loads((d/'request.json').read_text())['request']['generation']==0]
    if len(dirs)!=1 or not (dirs[0]/'response.json').exists():pytest.skip('optional closed local first session absent')
    d=dirs[0];steps=[json.loads(p.read_text()) for p in sorted(d.glob('step-*.completed.json'))]
    response=json.loads((d/'response.json').read_text())
    r=module.component_trace(steps,response)
    assert r['completed_steps']==14 and r['component_testing']['probe_attempts']==8
    assert len(r['same_fixture_later_code_comparisons'])==4
    assert all(c['transition']=='returned-to-raised' for c in r['same_fixture_later_code_comparisons'])
    assert not r['automatic_repair_claimed']


def test_full_export_checks_raw_inventory_and_rebuilds_all_files_twice(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path/'fixture',monkeypatch);raw=tmp_path/'raw';raw.mkdir()
    save(raw/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    for arm in p['arm_order']:
        records_path=raw/'search/run-00'/arm.replace(':','--')/'campaign/native-adaptive-state.json'
        records_path.parent.mkdir(parents=True)
        save(records_path,{'pending':None,'records':[records[arm,g] for g in (0,1)]})
    for author in a['authoring']:
        key=author['arm'],author['generation'];d=raw/('session-'+str(p['schedule'].index({k:author[k] for k in ('arm','generation')})))
        author['raw_directory']=str(d);inner=d/'authoring/generation-SCRIPTED';inner.mkdir(parents=True)
        save(inner/'response.json',{'definition':clone(author['definition']),'component_testing':clone(author['component_testing'])})
    a['raw_inventory_sha256']=digest(module._inventory(raw));seal(a)
    for name in ('audit-one','audit-two'):save(tmp_path/(name+'.json'),{k:v for k,v in a.items() if k!='content_sha256'})
    args=SimpleNamespace(run=raw,audit_one=tmp_path/'audit-one.json',audit_two=tmp_path/'audit-two.json',output=tmp_path/'one')
    module.export(args);args.output=tmp_path/'two';module.export(args)
    expected={'report.json','slots.csv','manifest.json','development-loss-paths.png','development-loss-paths.svg',
        'component-observations.png','component-observations.svg'}
    assert {p.name for p in (tmp_path/'one').iterdir()}==expected
    assert all((tmp_path/'one'/name).read_bytes()==(tmp_path/'two'/name).read_bytes() for name in expected)
    (raw/'unexpected.txt').write_text('SCRIPTED raw mutation')
    args.output=tmp_path/'three'
    with pytest.raises(ValueError,match='inventory'):module.export(args)
    assert not args.output.exists()


def test_different_audits_cannot_start_export(tmp_path):
    one=tmp_path/'one';two=tmp_path/'two';one.write_text('{}');two.write_text('{}\n')
    args=SimpleNamespace(run=tmp_path/'raw',audit_one=one,audit_two=two,output=tmp_path/'out')
    with pytest.raises(ValueError,match='audits differ'):module.export(args)
    assert not args.output.exists()
