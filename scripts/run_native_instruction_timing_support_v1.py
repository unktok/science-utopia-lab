"""Three prospective native advice controls, after audited fixed evaluation.

No designer, selection, project overwrite, inference retry or replacement.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, progress
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_benchmark_controls import objective_specs, selection_control
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone, digest
from utopia.system.native_information_institution import information_system, instruction_control
from utopia.system.native_liquidity_controls import liquidity_control
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-instruction-timing-support.v1'
AUDIT_SCHEMA = 'scienceutopia.native-instruction-timing-support-audit.v1'
PROTOCOL = 'research/protocols/campaigns/native-instruction-timing-support-v1.md'
CONTENT_LOSS = 'research/objectives/losses/native-common-content-utility-v1.json'
SEED = 61001
MESSAGE = (
    'When choosing your next research direction within the current four-year '
    'horizon, prefer a permitted direction with the shortest listed Expected '
    'Project Duration. Break ties using your own scientific judgment. Choose only '
    'a topic allowed by your normal task. Do not invent a duration or change the '
    "simulator's production, funding, review or publication rules. This is advice "
    'about your research choice, not an instruction to accept or reject papers.'
)
INPUT_KEYS = ('scientist', 'designer', 'data_cache', 'world', 'losses',
              'reference_systems', 'observer_contract')


def read(path): return checked(json.loads(Path(path).read_text()))
def utc(): return datetime.now(timezone.utc).isoformat()


def preceding_evidence(raw, analysis, source):
    """No preparation from a live, stopped or merely declared previous study."""
    raw, analysis, source = Path(raw).resolve(), Path(analysis).resolve(), Path(source).resolve()
    p, end = read(raw/'plan.json'), read(raw/'terminal.json')
    # The shared closure chain writes plain orchestration JSON, not a sealed
    # native journal. Verify its explicit file hashes; do not pretend it has
    # native_numeric_designer.save's public return type.
    proof = json.loads((analysis/'ended.json').read_text())
    analysis_start = json.loads((analysis/'started.json').read_text())
    one, two = analysis/'audit-1.json', analysis/'audit-2.json'
    if one.read_bytes() != two.read_bytes():
        raise ValueError('two matching original fixed-evaluation audits required')
    audit = read(one)
    if (p['schema'] != 'scienceutopia.native-objective-fixed-evaluation.v1.plan'
            or pinned_revision(source) != p['source_commit']
            or end['status'] != 'closed' or proof['status'] != 'closed'
            or end['schema'] != 'scienceutopia.native-objective-fixed-evaluation.v1.terminal'
            or end['completed_jobs'] != len(p['jobs'])
            or analysis_start['schema'] != 'scienceutopia.native-objective-fixed-evaluation-finish.v1'
            or analysis_start['plan_file_sha256'] != file_sha256(raw/'plan.json')
            or analysis_start['scientific_source_commit'] != p['source_commit']
            or audit['schema'] != 'scienceutopia.native-objective-fixed-evaluation-audit.v1'
            or audit['source_commit'] != p['source_commit']
            or audit['plan_sha256'] != p['content_sha256']
            or audit['closure']['terminal'] != end
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']
            or proof['audit_file_sha256'] != file_sha256(one)
            or file_sha256(analysis/'costs-1.json') != proof['cost_file_sha256']
            or (analysis/'costs-1.json').read_bytes() != (analysis/'costs-2.json').read_bytes()
            or digest(_inventory(raw)) != audit['raw_inventory_sha256']):
        raise ValueError('unchanged normally closed independently audited fixed evaluation required')
    preceding = {'run': str(raw), 'analysis': str(analysis), 'source':str(source),
                 'plan_file_sha256': file_sha256(raw/'plan.json'),
                 'terminal_file_sha256': file_sha256(raw/'terminal.json'),
                 'analysis_end_file_sha256': file_sha256(analysis/'ended.json'),
                 'analysis_start_file_sha256': file_sha256(analysis/'started.json'),
                 'audit_file_sha256': file_sha256(one),
                 'cost_file_sha256': proof['cost_file_sha256']}
    return {k: clone(p[k]) for k in INPUT_KEYS}, preceding


def build_plan(operator, *, source, observer_backend, preceding):
    expected_losses = {'throughput': objective_specs()['throughput'],
                       'content-utility': json.loads((ROOT/CONTENT_LOSS).read_text())}
    conditions = {'schema': 'scienceutopia.native-world-conditions.v1',
                  'initial_funding': 30, 'population_resource_profile': 'balanced_two_band',
                  'log_resource_ledger': True}
    if operator['losses'] != expected_losses or operator['world']['world_conditions'] != conditions:
        raise ValueError('unchanged declared T/U losses and original base30 world required')
    image = operator['scientist']['image_id']
    anchor = liquidity_control(selection_control(information_system(image, seed=SEED), rule='accept-all'), image)
    if operator['reference_systems']['reviewed-all-connected'] != anchor.to_dict():
        raise ValueError('exact reviewed-all M1 connected reference required')
    observer = make_contract(source_commit=source,
        provider={k: operator['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1000, critics=3)
    operational = {'source_commit', 'maximum_posts', 'content_sha256'}
    if ({k:v for k,v in observer.items() if k not in operational}
            != {k:v for k,v in operator['observer_contract'].items() if k not in operational}):
        raise ValueError('scientific observer definition changed')
    jobs = [{'identity': 'instruction-'+label, 'condition': label, 'seed': SEED,
             'system': instruction_control(anchor, image, instruction=MESSAGE,
                       delivery_phase=phase, connected=connected, first_period=1).to_dict()}
            for label, phase, connected in [('cut',2,False), ('early',2,True), ('late',235,True)]]
    experiment = {'protocol': PROTOCOL, 'role': 'developer-instruction-timing-support'}
    world = {**clone(operator['world']), 'source_commit': source, 'years': 4,
             'experiment': experiment, 'classification': 'actual-native-instruction-timing-support-v1',
             'measurement_adapter_contract': observer}
    return {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
            'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
            'launch_environment': clone(ENVIRONMENT), 'operator_inputs': clone(operator),
            'preceding': clone(preceding),
            **{k: clone(operator[k]) for k in ('scientist','designer','data_cache','losses')},
            'experiment': experiment, 'world': world, 'observer_contract': observer,
            'instruction': MESSAGE, 'instruction_utf8_sha256': hashlib.sha256(MESSAGE.encode()).hexdigest(),
            'jobs': jobs, 'budget': {'native_worlds_upper_bound':3, 'world_wall_seconds':7200,
                'scientist_HTTP_attempts_per_world':1024, 'observer_POSTs_upper_bound':1000,
                'designer_generation_POSTs':0, 'replace_failed_slots':False,
                'repeat_unfavorable_worlds':False},
            'development_seed_reused':True, 'held_out_evaluation':False,
            'policy_selection':False, 'publication_ready':False}


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean instruction source/runtime required')
    operator, preceding = preceding_evidence(p['preceding']['run'], p['preceding']['analysis'], p['preceding']['source'])
    if operator != p['operator_inputs'] or preceding != p['preceding']:
        raise ValueError('original preceding evidence differs')
    expected = build_plan(operator, source=p['source_commit'],
                          observer_backend=p['observer_contract']['backend'], preceding=preceding)
    if expected != {k:v for k,v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal message/conditions/budgets plan reconstruction differs')
    return p


def prepare(args):
    require_environment(); source = pinned_revision(ROOT)
    if (args.output.exists() or args.output.is_relative_to(args.preceding_run.resolve())
            or args.output.is_relative_to(args.preceding_analysis.resolve())):
        raise ValueError('fresh separate instruction assay required')
    operator, preceding = preceding_evidence(args.preceding_run, args.preceding_analysis, args.preceding_source)
    if not Path(operator['data_cache']).is_dir():
        raise ValueError('existing offline native corpus required')
    p = build_plan(operator, source=source, preceding=preceding,
        observer_backend=backend_binding({k:operator['scientist'][k] for k in ('model','model_digest')}))
    args.output.mkdir(parents=True); save(args.output/'plan.json',p); require_plan(args.output)
    print(json.dumps({'prepared_source':source, 'native_worlds_upper_bound':3, 'new_model_calls':0}),flush=True)


def observe(root, p, job, observer):
    directory = root/'controls'/job['identity']
    if (directory/'started.json').exists():
        raise ValueError('consumed control; no redispatch')
    suggestion = Suggestion(job['identity'],job['system'],0,'developer-instruction-timing-control')
    save(directory/'started.json', {'job':clone(job),'suggestion':suggestion.to_dict(),'started_utc':utc()})
    o = evaluate_native_suggestion(suggestion,seeds=[job['seed']],
        simulation_factory=factory_for(directory/'worlds',p,root),loss_spec=p['losses']['throughput'],
        measurement_adapter=measure_with(observer,p['observer_contract'])).to_dict()
    save(directory/'observation.json',o)
    scores = {k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()}
    save(directory/'cross-scores.json',scores)
    if o['status'] != 'complete' or any(s['status'] != 'complete' for s in scores.values()):
        raise ValueError('control world failed; no later inference or replacement')


def run(root):
    require_environment(); p = require_plan(root)
    with (root/'writer.lock').open('a') as owner, (Path(p['preceding']['run'])/'writer.lock').open('r') as previous:
        for h in (owner,previous): fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():
            raise ValueError('consumed assay; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],
                                  'started_utc':utc(),'pid':os.getpid()})
        complete = 0; status = 'stopped'; error = {}; stage = 'preparing'
        try:
            observer = CommonContentObserver(root/'observer',p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            for job in p['jobs']:
                stage=job['identity']; progress(root,'controls',stage)
                observe(root,p,job,observer); complete+=1; require_plan(root)
            audit=observer.audit()
            save(root/'observer-audit.json',{k:v for k,v in audit.items() if k!='content_sha256'})
            if read(root/'observer-audit.json') != audit:
                raise ValueError('saved original observer audit differs')
            status='closed';stage='closed';progress(root,'closed')
        except BaseException as e:
            error={'error_type':type(e).__name__,'error':str(e)};raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,
                'completed_jobs':complete,'ended_utc':utc(),'policy_selection':False,'publication_ready':False,**error})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True)
    for name in ('preceding-run','preceding-analysis','preceding-source'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();a.output=a.output.resolve()
    if a.stage=='prepare':
        if any(getattr(a,k) is None for k in ('preceding_run','preceding_analysis','preceding_source')):
            p.error('explicit prior fixed evaluation, source and audits required')
        prepare(a)
    else:run(a.output)


if __name__=='__main__':main()
