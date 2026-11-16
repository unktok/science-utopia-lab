"""Four-step native U/C optimization; explicit corrected feedback and endpoints.

Same24 own slots/27-world ceiling, not more populations or a new world/loss.
Historical studies retain their original plans, selections and source checkouts.
"""
import argparse
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path
import subprocess

from scripts import run_native_priority_method_comparison_v1 as legacy
from scripts.reports.stage_native_component_fixtures_v1 import collect, TOPIC_SCOPE
from utopia.optimization.blackbox import Suggestion, Observation
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_component_parameter_context_v1 import OPTION, SCOPE as PARAMETER_SCOPE, parameters
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_development_references import objective_view
from utopia.optimization.native_initial_choice_space_v1 import NativeInitialChoiceSpace
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_terminal_cost_controls_v1 import terminal_consolidation_control
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-corrected-choice-search.v1'
AUDIT_SCHEMA = SCHEMA + '.audit'
PROTOCOL = 'research/protocols/campaigns/native-corrected-choice-search-v1.md'
AUDIT_SCRIPTS = ['scripts/run_native_corrected_choice_search_v1.py', 'scripts/audit_native_corrected_choice_search_v1.py']
METHODS, OBJECTIVES, PARENTS, SEED = legacy.METHODS, legacy.OBJECTIVES, legacy.PARENTS, legacy.SEED
free, staged_author = legacy.free, legacy.staged_author
read, save, utc, literal = legacy.read, legacy.save, legacy.utc, legacy.literal
native_sources = legacy.native_sources
scientist_factory, designer_for = legacy.scientist_factory, legacy.designer_for
require_candidate, verify_interval = legacy.require_candidate, legacy.verify_interval
measurement, reconstruct_extra_measurement = legacy.measurement, legacy.reconstruct_extra_measurement
all_history_keys, history_keys = legacy.all_history_keys, legacy.history_keys
history_key, history_metadata = legacy.history_key, legacy.history_metadata
campaign, reference_context = legacy.campaign, legacy.reference_context
initial_readiness_jobs = legacy.initial_readiness_jobs
cold_numeric_slot, cold_numeric_end = legacy.cold_numeric_slot, legacy.cold_numeric_end


def history_directory(root, key):
    if key[1] != 0: raise ValueError('one declared optimizer history, not an unplanned replication')
    return legacy.history_directory(root, key)


def open_institutions(p):
    if (p.get('schema') != SCHEMA + '.plan' or p.get('protocol') != PROTOCOL
            or p.get('generations') != 4 or p.get('replication_seeds') != [79011]
            or p.get('designer_mode') != staged_author.MODE
            or p.get('design_space', {}).get('world_law_scope') != free.SCOPE
            or p.get('component_bank', {}).get(OPTION) != PARAMETER_SCOPE):
        raise ValueError('explicit corrected four-step native study required')
    return True


def build_plan(original, audit, *, source, origin, backend, observer_backend, bank, evidence, sources):
    if bank.get(OPTION) != PARAMETER_SCOPE or evidence.get('parameter_context_scope') != PARAMETER_SCOPE:
        raise ValueError('explicit attributed current-parameter bank overlay required')
    p = legacy.build_plan(original, audit, source=source, origin=origin, backend=backend,
        observer_backend=observer_backend, bank=bank, evidence=evidence, sources=sources)
    order = [(m, 0, o) for o in OBJECTIVES for m in METHODS]
    p.update(schema=SCHEMA + '.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT / PROTOCOL),
        replication_seeds=[79011], generations=4,
        schedule=[{'method':m, 'replication':r, 'objective':o, 'generation':g}
            for g in range(4) for m,r,o in (order if g % 2 == 0 else order[::-1])],
        numeric_settings={METHODS[0]:{'initial_random':4,'mutation_scale':.2},
            METHODS[1]:{'initial_random':1,'mutation_scale':.2}},
        numeric_kernels={METHODS[0]:'original uniform numeric priorities',
            METHODS[1]:'declared initial-choice rank mutation, not global adjacent swaps'},
        initial_choice_contract={'reference':PARENTS[0], 'period':1, 'node_id':'developer-catalog-agenda',
            'actor_fields':['id','can_author','is_active','project_end_year','expertise'],
            'record':'fresh reference exact successful native code context',
            'missing_optional_expertise_for_nonauthors':'preserve absence, never invent an author',
            'behavioral_change_or_merit_veto':False},
        selection_policy={'primary':'first minimum complete visible reference then chronological own; label origin',
            'secondary':'first minimum complete own, or none; no reference fallback',
            'old_own_only_selection_unchanged':True},
        experiment={'protocol':PROTOCOL,'role':'corrected-four-step-restricted-and-free-search'},
        independent_optimizer_replications=False)
    p['strategies']['local-workflow-designer']['protocol'] = PROTOCOL
    p['world'].update(experiment=clone(p['experiment']), classification='actual-native-corrected-choice-search-v1')
    p['comparison'].update(one_history_deeper_feedback_not_independent_replications=True,
        source_specific_package_comparison_not_isolated_causal_effect=True)
    open_institutions(p)
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean corrected-search source/runtime required')
    original, audit = free.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], bank=p['component_bank'], evidence=p['component_evidence'],
        sources=native_sources(original['original_native_sources']['original_source'], p['source_commit']))
    if literal(p) != expected: raise ValueError('literal corrected methods/world/loss/budget/selection plan differs')
    return p


def choice_projection(p, context):
    """Fresh pre-agenda actor fields, not retained historical scores or host guesses."""
    pair = context['pairs'][0]; observation = pair['observation']; contract = p['initial_choice_contract']
    candidate = p['reference_systems'][contract['reference']]
    if (pair['suggestion']['suggestion_id'] != 'workflow-reference-' + contract['reference']
            or observation['status'] != 'complete' or observation['candidate'] != candidate
            or len(observation['metadata']['runs']) != 1):
        raise ValueError('fresh exact complete zero-priority reference required for initial choice input')
    run = observation['metadata']['runs'][0]; checkpoint = Path(run['checkpoint_path']).resolve()
    cell = checkpoint.parents[3]
    if cell.name != run['run_id'] or checkpoint.relative_to(cell).parts[:3] != ('simulation','checkpoints','native-design'):
        raise ValueError('exact recorded reference checkpoint/cell layout required')
    path = cell / 'code-contexts.jsonl'
    if path.is_symlink(): raise ValueError('literal reference code journal required')
    before = file_sha256(path)
    node = next(n for n in candidate['mechanisms'] if n['mechanism_id'] == contract['node_id'])
    records = []
    for line in path.open():
        value = decode_json(line, strict=True, finite_floats=True)
        if value['context']['period'] == contract['period'] and value['artifact'] == node['parameters']['code_artifact']:
            records.append(validate_record(value))
    if len(records) != 1: raise ValueError('one literal first-year reference agenda invocation required')
    record = records[0]
    if (record['binding'] != {'source_commit':p['source_commit'], 'system_fingerprint':digest(candidate), 'run_id':run['run_id']}
            or record['context']['parameters'] != parameters(candidate, contract['node_id'])
            or file_sha256(path) != before):
        raise ValueError('fresh reference input/source/parameters differ')
    society = record['context']['inputs']['world']
    if len(society) != 1: raise ValueError('one actual native pre-agenda world required')
    actors = [{k:clone(a[k]) for k in contract['actor_fields'] if k in a}
        for a in society[0]['payload']['ecosystem']['agents']]
    return {'schema':SCHEMA+'.initial-choice-context', 'source_commit':p['source_commit'],
        'reference_observation_sha256':digest(observation), 'code_journal_path':str(path),
        'code_journal_file_sha256':before, 'original_bundle_sha256':record['bundle_sha256'],
        'actor_projection':actors, 'new_model_calls':0, 'new_native_worlds':0}


def require_choice(root, p, context):
    expected = choice_projection(p, context)
    if literal(read(root / 'initial-choice-context.json')) != expected:
        raise ValueError('initial choice context changed; no guessed/replacement actor projection')
    return expected


def parent_for(p, context, objective):
    return min(objective_view(context, p['losses'][objective])['observations'], key=lambda r:r['observation']['loss'])


def numeric_optimizer(p, context, key):
    method, rep, objective = key
    if key not in all_history_keys(p) or method not in p['numeric_settings']:
        raise ValueError('declared corrected numeric history required')
    parent = parent_for(p, context, objective); identity = parent['suggestion']['suggestion_id']
    base = SystemSpec.from_dict(p['literal_related_system'])
    if identity == 'workflow-reference-' + PARENTS[1]: base = terminal_consolidation_control(base, terminal_year=4)
    elif identity != 'workflow-reference-' + PARENTS[0]: raise ValueError('literal declared numeric parent required')
    space = (NativeInitialChoiceSpace(base, choice_projection(p, context)['actor_projection'])
        if method == METHODS[1] else topic_priority_space(base))
    if space.binding['anchor'] != parent['suggestion']['candidate']:
        raise ValueError('numeric anchor is not its measured exact parent')
    opt = NativeParameterOptimizer(space, seed=p['replication_seeds'][rep], **p['numeric_settings'][method])
    opt.warm_start(Observation.from_dict(parent['observation']))
    return opt


def endpoint(observations, *, reference_loss, complete_own):
    pool = [(origin,o) for origin,o in observations if o['status'] == 'complete']
    best = min((o['loss'] for _,o in pool), default=None)
    ties = [(origin,o) for origin,o in pool if o['loss'] == best]
    chosen = ties[0] if ties else None
    return {'loss':best, 'completed_submissions':complete_own,
        'all_tied_ids':[o['suggestion_id'] for _,o in ties],
        'selected_id':None if chosen is None else chosen[1]['suggestion_id'],
        'system':None if chosen is None else clone(chosen[1]['candidate']),
        'reference_loss':reference_loss, 'selected_origin':None if chosen is None else chosen[0]}


def selection(root, p, context):
    primary, own_only = ({m:{'0':{}} for m in METHODS} for _ in range(2))
    for key in all_history_keys(p):
        m,r,objective = key; directory = history_directory(root,key)
        if m == METHODS[2]:
            c = campaign(root,p,key,context)
            if c.state['pending'] is not None or len(c.state['records']) != 4:
                raise ValueError('all four free-author slots must be known terminal')
            own = [o for record in c.state['records'] for o in record['observations'] if o is not None]
        else: own = [read(directory / f'generation-{g}/observation.json') for g in range(4)]
        references = [row['observation'] for row in objective_view(context,p['losses'][objective])['observations']]
        reference_loss = min(o['loss'] for o in references); complete = sum(o['status']=='complete' for o in own)
        pairs = [('own',o) for o in own]
        own_only[m]['0'][objective] = endpoint(pairs,reference_loss=reference_loss,complete_own=complete)
        primary[m]['0'][objective] = endpoint([('reference',o) for o in references]+pairs,
            reference_loss=reference_loss,complete_own=complete)
    return {'schema':SCHEMA+'.selection', 'plan_sha256':p['content_sha256'], 'selected':primary,
        'own_only_selected':own_only, 'baseline_fallback':False, 'held_out_evaluation':False,
        'primary_is_measured_best_known_not_own_discovery':True}


def run(root):
    free.base.require_environment(); p = require_plan(root)
    if any(k.startswith('SCIENCE_UTOPIA_') and 'FIXTURE' in k for k in os.environ):
        raise ValueError('test-only HTTP fixtures cannot enter actual corrected search')
    with ExitStack() as stack:
        for path in sorted({root/'writer.lock',Path(p['origin']['run'])/'writer.lock'}):
            h=stack.enter_context(path.open('a' if path==root/'writer.lock' else 'r'))
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('consumed corrected study; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],
            'pid':os.getpid(),'started_utc':utc(),'exclusive_hardware_claimed':False,
            'shared_host_process_snapshot':subprocess.check_output(['ps','-axo','pid,ppid,%cpu,%mem,etime,comm'],text=True)})
        stage,consumed,observations,status='initial-readiness',0,0,'stopped'
        try:
            key,relative=initial_readiness_jobs(p)[0]; c=campaign(root,p,key,prototype=True)
            designer_for(root/relative/'author',p,root).calibrate(c._request([],c._validate(),1));require_plan(root)
            observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            pairs=[]
            for label in p['reference_order']:
                stage='references';free.base.progress(root,stage,label);directory=root/'references'/label
                s=Suggestion('workflow-reference-'+label,p['reference_systems'][label],0,'developer-reference')
                save(directory/'started.json',{'suggestion':s.to_dict(),'seed':SEED,'started_utc':utc()})
                o=evaluate_native_suggestion(s,seeds=[SEED],simulation_factory=scientist_factory(directory/'worlds',p,root),
                    loss_spec=p['losses']['throughput'],measurement_adapter=measurement(p,observer)).to_dict()
                save(directory/'observation.json',o);save(directory/'cross-scores.json',{k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()})
                if o['status']!='complete':raise ValueError('reference null retained; no fallback/refill')
                pairs.append({'suggestion':s.to_dict(),'observation':Observation.from_dict(o).to_dict()});observations+=1;require_plan(root)
            context=reference_context(p,pairs);save(root/'developer-reference-context.json',literal(context))
            save(root/'initial-choice-context.json',choice_projection(p,context));require_choice(root,p,context)
            opts={key:numeric_optimizer(p,context,key) for key in all_history_keys(p) if key[0]!=METHODS[2]}
            for key,opt in opts.items():save(history_directory(root,key)/'initial-state.json',opt.state_dict())
            for index,slot in enumerate(p['schedule']):
                require_choice(root,p,context);key,g=history_key(slot),slot['generation'];objective=key[2]
                save(root/'slots'/f'{index:03}.json',{'slot':clone(slot),'plan_sha256':p['content_sha256'],'started_utc':utc(),'world_seed':SEED})
                consumed+=1;directory=history_directory(root,key);free.base.progress(root,'optimization','/'.join(map(str,key))+':g'+str(g))
                if key in opts:
                    stage='numeric-optimization';opt=opts[key];target=directory/f'generation-{g}';s,=opt.ask()
                    save(target/'started.json',{'slot':clone(slot),'plan_sha256':p['content_sha256'],'suggestion':s.to_dict(),'optimizer_after_ask':opt.state_dict(),'started_utc':utc()})
                    o=evaluate_native_suggestion(s,seeds=[SEED],simulation_factory=scientist_factory(target/'worlds',p,root),
                        loss_spec=p['losses'][objective],measurement_adapter=measurement(p,observer))
                    save(target/'observation.json',o.to_dict());save(target/'cross-scores.json',{k:evaluate_loss(v,o.metadata['measurements']) for k,v in p['losses'].items()})
                    opt.tell([o]);save(target/'optimizer-after-tell.json',opt.state_dict());observations+=1
                else:
                    c=campaign(root,p,key,context)
                    if c.state['pending'] is not None or len(c.state['records'])!=g:raise ValueError('consumed/pending author slot; no redispatch')
                    req=c._request(c.state['records'],c._validate(),1);author=designer_for(directory/'authoring',p,root)
                    stage='readiness';cert=author.calibrate(req);require_plan(root)
                    def generate(request):
                        if request!=req:raise ValueError('proposal differs from calibrated actual request')
                        return free.base.generation_definition(author.execute(request,purpose='proposal',certificate=cert))
                    stage='free-optimization';record=c.advance(simulation_factory=scientist_factory(directory/'worlds',p,root),
                        generators={'local-workflow-designer':generate},count=1,measurement_adapter=measurement(p,observer),measurement_contract=p['observer_contract'])
                    observations+=sum(o is not None for o in record['observations'])
                require_plan(root);require_choice(root,p,context)
            save(root/'selection.json',selection(root,p,context));free.base.retain_observer_audit(root,observer)
            status=stage='closed';free.base.progress(root,stage,None)
        except BaseException as error:
            save(root/'failure.json',{'stage':stage,'error_type':type(error).__name__,'error':str(error),'consumed_slots':consumed,'no_retry':True});raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,'consumed_slots':consumed,
                'observations':observations,'ended_utc':utc(),'no_retry':True,'held_out_evaluation':False,'publication_ready':False})


def cold_numeric_begin(root,p,context):
    require_choice(root,p,context);states={}
    for key in all_history_keys(p):
        if key[0]==METHODS[2]:continue
        opt=numeric_optimizer(p,context,key)
        if literal(read(history_directory(root,key)/'initial-state.json'))!=opt.state_dict():raise ValueError('numeric initial state differs')
        states[key]={'optimizer':opt,'completed_slots':0}
    return states


def prepare(args):
    free.base.require_environment();source=pinned_revision(ROOT)
    origin={'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),
        'source_commit':read(args.audit_one)['source_commit'],'audit_files':{str(v.resolve()):file_sha256(v) for v in (args.audit_one,args.audit_two)}}
    output=args.output.resolve()
    if output.exists() or output.is_relative_to(args.origin_run.resolve()):raise ValueError('fresh separate corrected-study output required')
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);original,audit=free.preceding_evidence(origin)
        if not Path(original['data_cache']).is_dir():raise ValueError('existing offline corpus required')
        bank=collect(args.origin_run,args.audit_one,scope=TOPIC_SCOPE,source_root=args.origin_source)
        bank[OPTION]=PARAMETER_SCOPE;bank['content_sha256']=digest(bank)
        evidence={'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),
            'audit':str(args.audit_one.resolve()),'audit_file_sha256':file_sha256(args.audit_one),
            'staging_scope':TOPIC_SCOPE,'parameter_context_scope':PARAMETER_SCOPE}
        p=build_plan(original,audit,source=source,origin=origin,backend=backend_binding(original['designer']),
            observer_backend=backend_binding(original['scientist']),bank=bank,evidence=evidence,
            sources=native_sources(original['original_native_sources']['original_source'],source))
        output.mkdir(parents=True);save(output/'plan.json',p);require_plan(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','run'));parser.add_argument('--output',type=Path,required=True)
    for key in ('origin-run','origin-source','audit-one','audit-two'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args();args.output=args.output.resolve()
    if args.stage=='run':run(args.output);return
    if any(getattr(args,k) is None for k in ('origin_run','origin_source','audit_one','audit_two')):parser.error('exact closed original topic source/run and paired audits required')
    prepare(args)


if __name__=='__main__':main()
