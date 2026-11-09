"""Read-only M audit executed with the ORIGINAL frozen runtime, not a new one.

This analysis adapter lives separately from the active experiment. Its parent
launches the trusted script against an explicit clean frozen source; all native
imports/source checks occur there. No factory, model or code executor runs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def dossier_inputs(cell,saved,seed):
    """Match the real v30 rendered context, retaining ambiguous recipients.

    Raw audit hashes are aliased by the real renderer, so searching for literal
    raw messages would incorrectly report that nothing reached model inputs.
    M delivers at the end of a year; next-year prefixes retain every message.
    An identical rendered prefix can belong to several M2 recipients: do not
    turn that ambiguity into a one-to-one actor/request attribution.
    """
    import sqlite3
    from utopia.system.model_provenance_view import render_provenance_view
    from utopia.system.design_patch import digest
    from utopia.utils.seeding import derive_seed
    with sqlite3.connect((cell/'replies/responses.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        completed={row[0] for row in db.execute("SELECT payload_sha FROM replies WHERE outcome='response'")}
    wires=[json.loads(line) for line in (cell/'wire-requests.jsonl').read_text().splitlines()]
    matches=[];direction_years=[];initial=[]
    def text(payload):
        return '\n'.join(m.get('content','') if isinstance(m.get('content',''),str) else
            '\n'.join(p['text'] for p in m['content'] if p.get('type')=='text')
            for m in payload.get('messages',[]))
    for wire in wires:
        year=wire['year']
        if wire['payload_sha256'] not in completed or type(year) is not int:continue
        body=text(wire['payload']);actual_seed=wire['payload'].get('seed',wire['payload'].get('extra_body',{}).get('seed'))
        direction=actual_seed in {derive_seed(seed,'phase1_directions',year,i,a) for i in range(5) for a in range(3)}
        if direction and year==1:initial.append(wire['payload_sha256'])
        if 'native-research-history-dossier-v1' not in body:continue
        if direction:direction_years.append(year)
        candidates=[]
        for actor in saved['ecosystem_data']['agents']:
            prefix=[m for m in actor.get('institutional_context',[]) if m['received_year']<year]
            if prefix and render_provenance_view(prefix) in body:
                candidates.append({'actor_id':actor['id'],'raw_message_ids':[m['message_id'] for m in prefix],
                    'raw_prefix_sha256':digest(prefix)})
        matches.append({'year':year,'http_payload_sha256':wire['payload_sha256'],
            'direction_namespace_seed_match':direction,'possible_recipient_prefixes':candidates,
            'recipient_attribution':'unique-rendered-prefix' if len(candidates)==1 else
                'ambiguous-rendered-prefix' if candidates else 'marker-without-matched-complete-prefix'})
    return {'completed_dossier_inputs':matches,'first_direction_input_year':min(direction_years) if direction_years else None,
        'initial_direction_payload_hashes':sorted(initial),
        'scope':'Exact rendered-prefix occurrence, not beneficial interpretation; recipient ambiguity retained.'}


def worker(run,output):
    # These resolve in the explicitly selected frozen cwd/PYTHONPATH.
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.analyze_native_open_v7 import _inventory
    from utopia.optimization.native_numeric_designer import checked,replay_numeric
    from utopia.optimization.native_designer_preflight import runtime_binding
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.loss import evaluate_loss
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.native_information_institution import information_system
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    read=lambda path:checked(json.loads(Path(path).read_text()))
    run=Path(run).resolve();output=Path(output).resolve();source=Path.cwd()
    if output.is_relative_to(run):raise ValueError('audit output must not alter experiment records')
    plan=read(run/'plan.json');closure=read(run/'mechanisms-complete.json')
    if (plan['source_commit']!=pinned_revision(source) or plan['runtime']!=runtime_binding()
            or closure['plan_sha256']!=plan['content_sha256'] or closure['slots']!=12):
        raise ValueError('closed original source-bound mechanism study required')
    before=_inventory(run)
    sources=source_proofs(source,plan['source_commit'],scripts=['scripts/run_pre_scale_pilot_v1.py',
        'scripts/native_benchmark_physical.py'],resources=[plan['protocol'],
        'research/objectives/losses/native-joint-v5-throughput.json',
        'research/objectives/losses/native-reviewed-production-efficiency-v13.json'])
    if file_sha256(source/plan['protocol'])!=plan['protocol_sha256']:
        raise ValueError('original protocol differs')
    certificate=read(run/'numeric-readiness/certificate.json');numeric=[]
    for case in certificate['cases']:
        directory=run/case['journal_relative']
        if file_sha256(directory/'result.json')!=case['result_sha256']:
            raise ValueError('original numerical readiness terminal changed')
        numeric.append({'objective':case['objective'],'replayed_status':replay_numeric(directory)['status']})
    rows=[]
    for seed in plan['mechanism_seeds']:
        for condition in ('M0','M1','M2','M3'):
            identity=condition+'-s'+str(seed);root=run/'mechanisms'/identity
            start=read(root/'started.json');o=read(root/'observation.json')
            spec=information_system(plan['scientist']['image_id'],condition=condition,seed=seed)
            if (start['system']!=spec.to_dict() or start['plan_sha256']!=plan['content_sha256']
                    or o['candidate']!=spec.to_dict() or o['suggestion_id']!=identity
                    or o['status']!='complete' or o['metadata']['technical_failures']
                    or len(o['metadata']['runs'])!=1):
                raise ValueError('mechanism identity/specification/complete observation differs')
            expected_relative=str((root/'observation.json').relative_to(run))
            if closure['all_observation_file_sha256'].get(expected_relative)!=file_sha256(root/'observation.json'):
                raise ValueError('mechanism observation closure hash differs')
            cell=root/'worlds'/(identity+'-s'+str(seed))
            if {p.name for p in (root/'worlds').iterdir()}!={cell.name}:raise ValueError('unaccounted mechanism world')
            world={**plan['scientist'],'source_commit':plan['source_commit'],
                'runtime_seed_binding':{'python_hash_seed_environment':os.environ.get('PYTHONHASHSEED'),
                    'python_hash_probe':hash('scienceutopia.native-world.v1')},
                'experiment':{'protocol':plan['protocol'],'role':'mechanism-development',
                    'plan_sha256':plan['content_sha256']}}
            proof=physical_proof(cell,spec,world=world,seed=seed,years=4,evidence=o['metadata']['runs'][0])
            # Preserve the legacy literal-string probe under its own name;
            # it does not reconstruct v30 model-facing audit aliases.
            proof['legacy_literal_context_probe']=proof.pop('context_input_proof')
            if o['metadata']['measurements']!=[proof['measurement']]:raise ValueError('native independent measurement differs')
            scores={k:evaluate_loss(v,[proof['measurement']]) for k,v in plan['losses'].items()}
            recorded=read(root/'cross-scores.json');recorded.pop('content_sha256')
            if scores!=recorded or o['loss']!=scores['throughput']['loss']:
                raise ValueError('independent cross-objective loss reconstruction differs')
            state=read_portable_checkpoint(Path(o['metadata']['runs'][0]['checkpoint_path']))
            events=state['native_system']['events']
            if any(e['event_type']=='native.domain.project_applied' or
                e['event_type']=='native.system.research_plan_applied' and e['payload']['amendments'] for e in events):
                raise ValueError('M unexpectedly changed original project plans')
            inputs=dossier_inputs(cell,state,seed)
            rows.append({'id':identity,'condition':condition,'seed':seed,'scores':{k:v['loss'] for k,v in scores.items()},
                'measurement':proof['measurement'],'actual_inputs':inputs,'physical_proof':proof,
                'observation_file_sha256':file_sha256(root/'observation.json')})
    first_inputs=[]
    for seed in plan['mechanism_seeds']:
        current=[r for r in rows if r['seed']==seed]
        prefixes=[r['actual_inputs']['initial_direction_payload_hashes'] for r in current]
        first_inputs.append({'seed':seed,'same_first_direction_payload_multisets':
            bool(prefixes[0]) and all(p==prefixes[0] for p in prefixes),
            'counts':[len(p) for p in prefixes],
            'not_a_claim_of_coupled_future_fresh_replies':True})
    if before!=_inventory(run):raise ValueError('original raw files changed during read-only audit')
    result={'schema':'scienceutopia.pre-scale-information-audit.v1','source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'numeric_readiness':numeric,'rows':rows,
        'first_direction_input_comparisons':first_inputs,'source_proof':sources,
        'raw_inventory_sha256':digest(before),'raw_files':len(before),
        'analysis_adapter_sha256':file_sha256(Path(__file__)),
        'analysis_scope':'New explicit analysis adapter executing unchanged original-source native libraries.',
        'new_model_calls':0,'new_code_executions':0,'scientific_or_optimizer_superiority':False}
    result['content_sha256']=digest(result)
    write_json_atomic(output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'audit':str(output),'content_sha256':result['content_sha256'],'normal_worlds':len(rows)}))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frozen-source',type=Path)
    p.add_argument('--worker',action='store_true');args=p.parse_args()
    if args.worker:worker(args.run,args.output);return
    if args.frozen_source is None:raise ValueError('explicit original frozen source checkout required')
    root=args.frozen_source.resolve();script=Path(__file__).resolve()
    if not (args.run/'mechanisms-complete.json').exists():raise ValueError('study is not closed; do not audit a running writer')
    before=hashlib.sha256(script.read_bytes()).hexdigest()
    command=[sys.executable,'-c','import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(root),str(script),'--worker','--run',str(args.run.resolve()),'--output',str(args.output.resolve())]
    result=subprocess.run(command,cwd=root,env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=before:raise ValueError('analysis adapter changed during audit')
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
