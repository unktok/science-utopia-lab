"""Synthetic CLOSED-study projection QA. No real evidence, designer or simulator."""
from copy import deepcopy
import json

import pytest

from scripts.reports import native_design_benchmark as report
from tests.reports.test_native_design_benchmark_plan import plan
from utopia.system.design_patch import digest


def hashed(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def fixture():
    p=plan();p['classification']='SCRIPTED-projection-QA-only';hashed(p);run_data={}
    for run,bindings in p['campaign_bindings'].items():
        run_data[run]={}
        for arm,binding in bindings.items():
            own=p['assignments'][arm]['objective'];rows=[]
            for g in range(4):
                scores={loss['id']:float(-g-1) for loss in p['losses'].values()}
                if g==2:scores={key:None for key in scores}
                rows.append({'generation':g,'cross_scores':scores,'own_loss':scores[p['losses'][own]['id']],
                    'status':'technical-failure' if g==2 else 'complete',
                    'system_fingerprint':'SCRIPTED-system','checkpoint_sha256':None if g==2 else 'SCRIPTED-checkpoint',
                    'metrics':None,'lineage':{'scope':'SCRIPTED'},
                    'physical_proof':None if g==2 else {'response_proof':{'researcher_responses':1,'wire_requests':1},
                        'code_proof':{'recorded_executions':0}}})
            run_data[run][arm]={'binding':binding,'terminal':True,'pending':None,'consumed_native_slots':4,
                'observations':rows,'physical_native_worlds':3,'physical_world_directory_count':4,
                'physical_researcher_responses':3,'physical_wire_requests':3,
                'recorded_code_executions_including_partial':0,'completed_researcher_model_call_seconds':1.}
    selected={arm:{'system':p['initial_system'],'policy_sha256':'SCRIPTED-policy','all_tied_row_ids':['SCRIPTED'],
        'selected_row_id':'SCRIPTED','loss':-4.} for arm in p['assignments']}
    selection=hashed({'schema':report.SCHEMA+'.selection','plan_sha256':p['content_sha256'],
        'selected':selected,'pooled':{},'all_rows':[],'reference_systems':p['reference_systems']})
    jobs=[];evaluated={}
    conditions=[(s,2) for s in p['evaluation']['seeds']]+[(31001,4)]
    for seed,years in conditions:
        job={'job_id':'SCRIPTED-'+str(seed)+'-'+str(years),'policy_sha256':'SCRIPTED-policy',
            'labels':['reference:'+name for name in p['reference_systems']]+['selected:'+arm for arm in selected],
            'seed':seed,'years':years}
        jobs.append(job)
        scores={k:{'loss':None if seed==31013 or seed==31019 and k!='throughput' else -7.} for k in p['losses']}
        evaluated[job['job_id']]={'scores':scores,'observation':{
            'status':'failed' if seed==31013 else 'complete',
            'metadata':{'measurements':[],'technical_failures':[{'error':'SCRIPTED'}] if seed==31013 else []}},
            'physical_proof':{'response_proof':{'researcher_responses':1,'wire_requests':1}}}
    a=hashed({'schema':report.SCHEMA+'.audit','source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
        'source_proofs':{'status':'verified-exact-source-closure','files':{'SCRIPTED-only':'not-a-real-source-proof'}},
        'raw_inventory_unchanged':True,'new_model_calls':0,'new_code_executions':0,
        'selection':selection,'runs':run_data,'references':{name:{'scores':{k:{'loss':0.} for k in p['losses']}}
            for name in p['reference_systems']},'evaluation_jobs':jobs,'evaluated':evaluated,
        'writer':{'started':{'started_utc':'2026-11-07T00:00:00+00:00'},
            'ended':{'ended_utc':'2026-11-07T01:00:00+00:00','status':'exited','exit_code':0}},
        'certificates':{},'designer_loads':[]})
    return p,a


def test_complete_projection_retains_all_slots_nulls_shared_jobs_and_separate_horizons():
    p,a=fixture();before=deepcopy(a)
    r=report.project(p,a,expected_source=p['source_commit'])
    assert a==before and r==report.project(p,a,expected_source=p['source_commit'])
    assert len(r['all_candidate_rows'])==120 and r['physical_evaluation_jobs']==6
    assert r['logical_evaluation_labels']==19 and r['wall_seconds']==3600.
    own=r['search_arms']['run-00']['throughput:parameters']
    assert [row['own_loss'] for row in own['rows']]==[-1.,-2.,None,-4.]
    assert [row['best_including_initial_so_far'] for row in own['rows']]==[-1.,-2.,-2.,-4.]
    assert r['search_arms']['run-00']['throughput:random']['designer_absent_by_design']
    paired=r['paired_vs_all_references']['throughput:parameters']['legacy']
    assert paired['throughput']['2']['summary']['available']==4
    assert paired['selective']['2']['summary']['available']==3
    assert paired['selective']['2']['summary']['values']==[0.,None,None,0.,0.]
    assert all(pair['physically_shared'] for pair in paired['throughput']['2']['pairs'])
    assert paired['throughput']['4']['single_seed_diagnostic']
    assert paired['throughput']['4']['summary']['scheduled']==1  # never pool year2+year4
    assert r['content_sha256']==digest({k:v for k,v in r.items() if k!='content_sha256'})
    assert r['interpretation']['projection_is_not_a_new_raw_audit']


@pytest.mark.parametrize('mutate',[
    lambda a:a.update(source_commit='e'*40),
    lambda a:a['runs']['run-00']['throughput:parameters'].update(pending={'SCRIPTED':True}),
    lambda a:a['runs']['run-00']['throughput:parameters']['observations'][2].update(own_loss=999.),
    lambda a:a['evaluation_jobs'].pop(),
    lambda a:a['evaluation_jobs'][0]['labels'].append('selected:UNDECLARED'),
    lambda a:a['writer']['ended'].update(status='aborted'),
])
def test_rehashed_incomplete_or_inconsistent_inputs_are_not_reported_as_complete(mutate):
    p,a=fixture();mutate(a);hashed(a)
    with pytest.raises(ValueError):report.project(p,a,expected_source=p['source_commit'])


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),'1'])
def test_nonfinite_or_boolean_scores_are_not_statistics(bad):
    with pytest.raises(ValueError):report.descriptive([{'x':bad}],'x')


def test_all_missing_has_no_fabricated_zero_and_cli_cannot_overwrite_raw(tmp_path):
    d=report.descriptive([{'x':None}]*5,'x')
    assert d['mean'] is None and d['population_sd'] is None and d['missing']==5
    p,a=fixture();raw=tmp_path/'raw';raw.mkdir()
    plan_file=raw/'plan.json';plan_file.write_text(json.dumps(p))
    audit_file=tmp_path/'audit.json';audit_file.write_text(json.dumps(a))
    output=tmp_path/'report.json'
    argv=['--plan',str(plan_file),'--audit',str(audit_file),'--expected-source',p['source_commit'],'--output',str(output)]
    assert report.main(argv)==0
    before=output.read_bytes()
    with pytest.raises(SystemExit):report.main(argv)
    assert output.read_bytes()==before
    with pytest.raises(SystemExit):report.main(argv[:-1]+[str(raw/'not-allowed.json')])


def test_print_history_projection_binds_input_and_does_not_modify_or_impute_nulls(tmp_path):
    from scripts.figures.native_design_benchmark import plot_search
    p,a=fixture();r=report.project(p,a,expected_source=p['source_commit']);before=deepcopy(r)
    manifest=plot_search(r,tmp_path/'figures')
    assert r==before and manifest['null_losses_imputed'] is False
    assert len(manifest['files'])==4 and manifest['input_report_content_sha256']==r['content_sha256']
    assert (tmp_path/'figures/selective-paths.png').exists()
    with pytest.raises(ValueError,match='fresh'):plot_search(r,tmp_path/'figures')
