"""Finite free-institution T/P pilot in the original capacity-limited world."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from scripts.run_native_institution_loop_v1 import readiness
from scripts.run_native_objective_instrument_loop_v1 import factory_for, feedback_for, progress
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_active_founders import measure, METRIC
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs, selection_control, without_review
from utopia.optimization.native_bounded_staged_designer import execute
from utopia.optimization.native_causal_design import OPTION, PRESENTATION
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_post_edit_feedback_v1 import OPTION as TEST_OPTION
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_capacity_controls import capacity_allocation_control
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.system.native_liquidity_controls import liquidity_control
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-capacity-objective-loop.v1'
PROTOCOL = 'research/protocols/campaigns/native-capacity-objective-loop-v1.md'
BANK_MANIFEST = 'research/data/native-resource-component-fixtures-v2/summary.json'
P_LOSS = 'research/objectives/losses/native-active-founder-boundaries-v1.json'
SEED = 61001
OBJECTIVES = ('throughput', 'founder-activity')


def read(path): return checked(json.loads(Path(path).read_text()))


def preceding_descriptor(evaluation, controls):
    """Require actual normal parent closures, without importing observations."""
    from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
    from scripts.finish_native_instruction_summary_v1 import wait_reports
    evaluation, controls = Path(evaluation).resolve(), Path(controls).resolve()
    for path in (evaluation/'ended.json', controls/'ended.json'):
        if not path.is_file():raise ValueError('closed preceding evaluation and controls required')
    end = read(evaluation/'ended.json'); start = read(evaluation/'started.json')
    audit = wait_analysis(evaluation/'audits',seconds=1)
    control_end = wait_reports(controls,seconds=1)
    raw = Path(start['evaluation_output']); plan = read(raw/'plan.json')
    if (start['schema']!='scienceutopia.native-objective-evaluation-continuation.v1'
            or end['status']!='closed' or end['candidate_reselection'] is not False
            or end['evaluation_plan_file_sha256']!=file_sha256(raw/'plan.json')
            or any(s['exit_code']!=0 for s in end['steps'])
            or end['audit_file_sha256']!=audit['audit_file_sha256']
            or plan['source_commit']!=start['source_commit']
            or pinned_revision(Path(start['evaluation_source']))!=plan['source_commit']):
        raise ValueError('normally closed immutable original evaluation required')
    return {'evaluation_chain':str(evaluation),'control_chain':str(controls),
        'evaluation_end_file_sha256':file_sha256(evaluation/'ended.json'),
        'evaluation_audit_file_sha256':audit['audit_file_sha256'],
        'evaluation_cost_file_sha256':audit['cost_file_sha256'],
        'control_end_file_sha256':file_sha256(controls/'ended.json'),
        'control_plan_file_sha256':control_end['assay_plan_file_sha256'],
        'losses_reused_as_development_observations':False}


def build_plan(operator, *, source, backend, bank, bank_file_hash, support, preceding):
    validate_designer_binding(operator['designer'], scientist_binding=operator['scientist'])
    manifest = read(ROOT/BANK_MANIFEST); checked(bank)
    if (bank_file_hash != manifest['bank_file_sha256'] or bank['content_sha256'] != manifest['bank_content_sha256']
            or len(source) != 40 or any(c not in '0123456789abcdef' for c in source)):
        raise ValueError('exact clean source and literal historical component bank required')
    image = operator['scientist']['image_id']
    if any(r['receipt']['image_id'] != image for r in bank['records']):
        raise ValueError('component bank executor differs')
    base = selection_control(information_system(image, seed=SEED), rule='accept-all')
    anchor = liquidity_control(base, image)
    references = {'reviewed-all-equalization':anchor.to_dict(),
        'reviewed-all-transfer-cut':liquidity_control(base,image,connected=False).to_dict(),
        'no-review-all-equalization':without_review(anchor).to_dict(),
        'reviewed-all-reserve-proximity':capacity_allocation_control(base,image,rule='reserve-proximity').to_dict(),
        'reviewed-all-completion-priority':capacity_allocation_control(base,image,rule='completion-priority').to_dict()}
    contract = {'schema':SCHEMA+'.measurement', 'source_commit':source, 'metric_id':METRIC,
        'instrument_sha256':file_sha256(ROOT/'utopia/optimization/native_active_founders.py'),
        'cohort':'initial author-capable actors', 'boundaries':'years1..4, excluding year0',
        'absent_founder_contribution':0, 'new_model_calls':0, 'adoption_constraint':False}
    experiment = {'protocol':PROTOCOL, 'role':'native-capacity-objective-conditioned-institutions'}
    world = {**clone(operator['scientist']), 'source_commit':source, 'years':4, 'experiment':experiment,
        'runtime_seed_binding':clone(operator['world']['runtime_seed_binding']),
        'world_conditions':{'schema':'scienceutopia.native-world-conditions.v2', 'initial_funding':30,
            'population_resource_profile':'balanced_two_band', 'log_resource_ledger':True,
            'papers_per_project':2, 'funding_budget_mode':'fixed', 'funding_budget_slots_frac':.2},
        'measurement_adapter_contract':contract, 'classification':'actual-native-capacity-objective-loop-v1'}
    post_edit = feedback_for(bank, source, image).contract
    return {'schema':SCHEMA+'.plan', 'source_commit':source, 'runtime':runtime_binding(),
        'protocol':PROTOCOL, 'protocol_sha256':file_sha256(ROOT/PROTOCOL), 'launch_environment':clone(ENVIRONMENT),
        'scientist':clone(operator['scientist']), 'designer':clone(operator['designer']), 'backend':clone(backend),
        'data_cache':operator['data_cache'], 'world':world, 'experiment':experiment, 'preceding':clone(preceding),
        'measurement_contract':contract, 'losses':{'throughput':objective_specs()['throughput'],
            'founder-activity':json.loads((ROOT/P_LOSS).read_text())},
        'reference_systems':references, 'reference_order':list(references), 'initial_system':anchor.to_dict(),
        'design_space':allow_review_routing(anchor,information_design_space(anchor,'code-and-graph',fixed_production=True)),
        'strategies':{'local-designer':{'kind':'code-and-graph','protocol':PROTOCOL,
            OPTION:True,PRESENTATION:'inline',TEST_OPTION:post_edit}},
        'component_bank':clone(bank), 'component_bank_file_sha256':bank_file_hash,
        'fixture_manifest_file_sha256':file_sha256(ROOT/BANK_MANIFEST), 'post_edit_contract':post_edit,
        'component_support':clone(support), 'objectives':list(OBJECTIVES), 'generations':2, 'optimizer_seed':65011,
        'schedule':[{'objective':o,'generation':g} for g in range(2) for o in (OBJECTIVES if g==0 else OBJECTIVES[::-1])],
        'budget':{'reference_worlds':5,'candidate_slots':4,'development_native_worlds_upper_bound':9,
            'scientist_HTTP_attempts_per_world':1024,'world_wall_seconds':7200,
            'readiness_sessions':5,'readiness_POSTs_per_session':40,'readiness_seconds':1200,
            'proposal_POSTs_per_session':16,'proposal_seconds':1800,'component_attempts_per_proposal':64,
            'critic_POSTs':0,'replace_failed_slots':False}, 'development_seed_reused':True,
        'reference_parent_policy':'best assigned loss across common references and own complete history',
        'final_selection_policy':'earliest tied complete own literal submission; no automatic fallback',
        'held_out_evaluation':False, 'publication_ready':False}


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean capacity study source/runtime required')
    expected = build_plan(p,source=p['source_commit'],backend=p['backend'],bank=p['component_bank'],
        bank_file_hash=p['component_bank_file_sha256'],support=p['component_support'],preceding=p['preceding'])
    if expected != {k:v for k,v in p.items() if k!='content_sha256'}:
        raise ValueError('exact capacity plan reconstruction differs')
    if preceding_descriptor(p['preceding']['evaluation_chain'],p['preceding']['control_chain'])!=p['preceding']:
        raise ValueError('preceding studies changed; no imported observations or retry')
    support = Path(p['component_support']['directory']); summary = read(support/'summary.json')
    if (file_sha256(support/'summary.json') != p['component_support']['summary_file_sha256']
            or file_sha256(support/'plan.json') != p['component_support']['plan_file_sha256']
            or summary['status']!='closed' or len(summary['observations'])!=12
            or not all(o['original_result_matches'] for o in summary['observations'])
            or read(support/'plan.json')['bank_file_sha256']!=p['component_bank_file_sha256']):
        raise ValueError('unchanged historical twelve-call component support required')
    return p


def measured(p):
    def append(sim,base):
        return {**measure(sim,base),'measurement_adapter_contract_sha256':digest(p['measurement_contract'])}
    return append


def campaign(root,p,objective,context=None,*,prototype=False):
    kwargs = {} if context is None else {'development_references':context}
    directory = root/'initial-readiness/campaign' if prototype else root/'search'/objective/'campaign'
    return NativeAdaptiveDesignCampaign(directory,initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective],seeds=[SEED],world_binding=p['world'],strategies=p['strategies'],
        mode='blackbox',seed=p['optimizer_seed'],design_space=p['design_space'],**kwargs)


def selection(root,p,context,*,frozen_utc=None,campaign_loader=None):
    from scripts.run_native_objective_instrument_loop_v1 import utc
    load = campaign if campaign_loader is None else campaign_loader; selected = {}
    for objective in p['objectives']:
        c = load(root,p,objective,context)
        if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
            raise ValueError('all four terminal own proposal slots required')
        pool = [o for r in c.state['records'] for o in r['observations']
                if o and o['status']=='complete' and o['loss'] is not None]
        best = min((o['loss'] for o in pool),default=None); ties = [o for o in pool if o['loss']==best]
        selected[objective] = {'loss':best,'all_tied_ids':[o['suggestion_id'] for o in ties],
            'selected_id':ties[0]['suggestion_id'] if ties else None,
            'system':clone(ties[0]['candidate']) if ties else None,'completed_submissions':len(pool)}
    return {'schema':SCHEMA+'.selection','plan_sha256':p['content_sha256'],'selected':selected,
        'baseline_fallback':False,'frozen_utc':utc() if frozen_utc is None else frozen_utc,'held_out_evaluation':False}


def observe(root,p,label):
    from scripts.run_native_objective_instrument_loop_v1 import utc
    directory = root/'references'/label; identity = 'reference-'+label
    if (directory/'started.json').exists(): raise ValueError('consumed reference; no redispatch')
    suggestion = Suggestion(identity,p['reference_systems'][label],0,'developer-reference')
    save(directory/'started.json',{'suggestion':suggestion.to_dict(),'seed':SEED,'started_utc':utc()})
    result = evaluate_native_suggestion(suggestion,seeds=[SEED],simulation_factory=factory_for(directory/'worlds',p,root),
        loss_spec=p['losses']['throughput'],measurement_adapter=measured(p)).to_dict()
    save(directory/'observation.json',result)
    scores = {k:evaluate_loss(v,result['metadata']['measurements']) for k,v in p['losses'].items()}
    save(directory/'cross-scores.json',scores)
    if result['status']!='complete' or any(v['status']!='complete' for v in scores.values()):
        raise ValueError('common reference failed; no replacement')
    return {'suggestion':suggestion.to_dict(),'observation':result}


def run(root):
    from scripts.run_native_objective_instrument_loop_v1 import utc
    require_environment(); p = require_plan(root)
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('consumed study; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],'started_utc':utc(),'pid':os.getpid()})
        status,stage,complete,failure = 'stopped','initial-readiness',0,{}
        try:
            prototype = campaign(root,p,'throughput',prototype=True)
            request = prototype._request([],prototype._validate(),1)
            progress(root,stage)
            readiness(root,p,request=request,numeric=False,target=root/'initial-readiness')
            pairs = []
            for label in p['reference_order']:
                stage='references'; progress(root,stage,label); pairs.append(observe(root,p,label)); complete+=1; require_plan(root)
            context = build_context(pairs,world=p['world'],seeds=[SEED],loss_spec=p['losses']['throughput'])
            save(root/'developer-reference-context.json',{k:v for k,v in context.items() if k!='content_sha256'})
            save(root/'developer-reference-context-ready.json',{'context_sha256':context['content_sha256'],
                'complete_references':5,'completed_utc':utc()})
            for slot in p['schedule']:
                objective,g=slot['objective'],slot['generation']; c=campaign(root,p,objective,context)
                if c.state['pending'] is not None or len(c.state['records'])!=g:
                    raise ValueError('pending/consumed proposal cannot be redispatched')
                request=c._request(c.state['records'],c._validate(),1); directory=root/'search'/objective
                stage='readiness'; progress(root,stage,objective+':g'+str(g))
                cert=readiness(root,p,request=request,numeric=False,target=directory/f'readiness-{g}')
                def generate(req):
                    return execute(directory/'authoring'/('generation-'+digest(req)),kind='proposal',request=req,
                        provider=p['designer'],source_commit=p['source_commit'],certificate=cert,seconds=1800,
                        inference_lock=root/'inference.lock',post_edit_bank=p['component_bank'])
                stage='optimization'; progress(root,stage,objective+':g'+str(g))
                c.advance(simulation_factory=factory_for(directory/'worlds',p,root),generators={'local-designer':generate},count=1,
                    measurement_adapter=measured(p),measurement_contract=p['measurement_contract'])
                require_plan(root)
            save(root/'selection.json',selection(root,p,context)); status=stage='closed'; progress(root,stage)
        except BaseException as error:
            failure={'error_type':type(error).__name__,'error':str(error)}; raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,'ended_utc':utc(),
                'complete_references':complete,'held_out_evaluation':False,'publication_ready':False,**failure})


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('stage',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True)
    for name in ('operator-plan','bank','component-support'):p.add_argument('--'+name,type=Path)
    for name in ('closed-evaluation','closed-controls'):p.add_argument('--'+name,type=Path)
    a=p.parse_args(); a.output=a.output.resolve()
    if a.stage=='run':run(a.output);return
    require_environment()
    if a.output.exists() or any(getattr(a,k) is None for k in ('operator_plan','bank','component_support','closed_evaluation','closed_controls')):
        p.error('fresh output and explicit existing operator/bank/support required')
    operator=read(a.operator_plan); bank=read(a.bank); support=a.component_support.resolve()
    if not Path(operator['data_cache']).is_dir():raise ValueError('existing offline native corpus required')
    plan=build_plan(operator,source=pinned_revision(ROOT),backend=backend_binding(operator['designer']),bank=bank,
        bank_file_hash=file_sha256(a.bank),support={'directory':str(support),
            'plan_file_sha256':file_sha256(support/'plan.json'),'summary_file_sha256':file_sha256(support/'summary.json')},
        preceding=preceding_descriptor(a.closed_evaluation,a.closed_controls))
    a.output.mkdir(parents=True); save(a.output/'plan.json',plan); require_plan(a.output)


if __name__=='__main__':main()
