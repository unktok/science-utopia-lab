"""Freeze both corrected endpoint scopes; never invent an own reference label.

Pure preparation only: no unused-seed attestation, dispatch or policy scoring.
"""
from scripts.native_design_benchmark_plan import policy_identity
from scripts.reports.native_priority_method_readout_v1 import analyze, CORRECTED_SCHEMA, METHODS, OBJECTIVES
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest

SCHEMA='scienceutopia.native-corrected-choice-fixed-bank.v1'
SCOPES=('best-known','own-only')


def seal(value):return {**value,'content_sha256':digest(value)}


def label(scope,method,objective):return 'selected/'+scope+'/'+method+'/history-0/'+objective


def freeze_bank(plan,audit,slots,references):
    report=analyze(plan,audit,slots,references)
    if report['schema']!=CORRECTED_SCHEMA:raise ValueError('explicit corrected four-step endpoint bank required')
    entries=[{'label':'reference/'+name,'role':'reference','reference_label':name,
        'system':clone(references[name]['candidate']),'selection_available':True,
        'development_cross_scores':clone(report['references'][index]['cross_scores']),
        'optimizer_visible':report['references'][index]['visible_parent']}
        for index,name in enumerate(plan['reference_order'])]
    for scope in SCOPES:
        rows=report['selected' if scope=='best-known' else 'own_only_selected']
        for row in rows:
            method,objective=row['method'],row['objective']
            original=audit['selection']['selected' if scope=='best-known' else 'own_only_selected'][method]['0'][objective]
            entries.append({'label':label(scope,method,objective),'role':scope+'-selection',
                'selection_scope':scope,'method':method,'optimizer_history':0,'objective':objective,
                'selected_origin':original['selected_origin'],'selected_id':original['selected_id'],
                'selected_cell_id':row['cell_id'],'system':clone(original['system']),
                'selection_available':original['system'] is not None,'development_loss':row['loss'],
                'development_cross_scores':clone(row['cross_scores']),'all_tied_ids':clone(original['all_tied_ids']),
                'completed_own_submissions':original['completed_submissions']})
    return seal({'schema':SCHEMA,'scientific_source_commit':plan['source_commit'],
        'origin_plan_content_sha256':plan['content_sha256'],'origin_audit_content_sha256':audit['content_sha256'],
        'origin_selection_content_sha256':audit['selection']['content_sha256'],
        'development_world_seed':plan['initial_system']['initial_state']['seed'],
        'losses':clone(plan['losses']),'reference_order':clone(plan['reference_order']),'entries':entries,
        'missing_own_selections':[e['label'] for e in entries if e.get('selection_scope')=='own-only' and not e['selection_available']],
        'candidate_reselection':False,'reference_fallback':False,'dispatchable':False,'seed_usage_validated':False,
        'new_model_calls':0,'new_native_worlds':0,
        'scope':'All3 references/6 best-known/6 own-only labels; returned references are not own inventions. '
            'Exact literal policy sharing only; labels/steps are not independent populations.'})


def planned_jobs(bank,seeds):
    checked(bank)
    if (bank['schema']!=SCHEMA or any(bank[k] for k in ('candidate_reselection','reference_fallback','dispatchable','seed_usage_validated'))
            or type(seeds) is not list or not 1<=len(seeds)<=3
            or any(type(s) is not int or not 0<=s<2**31 or s==bank['development_world_seed'] for s in seeds)
            or len(set(seeds))!=len(seeds)):
        raise ValueError('literal frozen corrected bank and explicit finite non-development seed draft required')
    entries=bank['entries'];refs,selected=entries[:3],entries[3:]
    expected=[(scope,m,o) for scope in SCOPES for m in METHODS for o in OBJECTIVES]
    if (len(refs)!=3 or len(selected)!=12 or len({e['label'] for e in entries})!=15
            or [e['label'] for e in refs]!=['reference/'+s for s in bank['reference_order']]
            or [e['reference_label'] for e in refs]!=bank['reference_order']
            or any(e['role']!='reference' or not e['selection_available'] or e['system'] is None for e in refs)
            or [(e['selection_scope'],e['method'],e['objective']) for e in selected]!=expected
            or [e['label'] for e in selected]!=[label(*key) for key in expected]
            or any(e['optimizer_history']!=0 or e['role']!=e['selection_scope']+'-selection' for e in selected)
            or any(e['selection_available']!=(e['system'] is not None) for e in entries)
            or any(e['selected_origin'] not in ('reference','own') for e in selected if e['selection_available'])
            or any(e['selected_origin'] not in ('own',None) for e in selected if e['selection_scope']=='own-only')
            or any(not e['selection_available'] for e in selected if e['selection_scope']=='best-known')
            or any(e['selected_origin'] is not None or e['selected_id'] is not None or e['selected_cell_id'] is not None
                for e in selected if not e['selection_available'])
            or any((e['selected_cell_id'] is None)!=(e['selected_origin']=='reference') for e in selected if e['selection_available'])
            or [e['label'] for e in selected if e['selection_scope']=='own-only' and not e['selection_available']]!=bank['missing_own_selections']):
        raise ValueError('all15 exact ordered reference/best-known/own-only labels and origins required')
    policies={}
    for entry in entries:
        if entry['system'] is None:continue
        identity=policy_identity(entry['system'])
        policies.setdefault(identity,{'system':entry['system'],'labels':[]})['labels'].append(entry['label'])
    jobs=[]
    for identity,policy in policies.items():
        for seed in seeds:
            system=clone(policy['system']);system['initial_state']['seed']=seed
            if policy_identity(system)!=identity:raise ValueError('seed binding changes literal policy')
            jobs.append({'identity':'evaluation-'+str(len(jobs)).zfill(3),'policy_sha256':identity,
                'seed':seed,'labels':clone(policy['labels']),'system':system})
    return seal({'schema':SCHEMA+'.job-draft','bank_content_sha256':bank['content_sha256'],'seeds':clone(seeds),
        'jobs':jobs,'logical_policy_labels':15,'missing_own_selections':clone(bank['missing_own_selections']),
        'maximum_physical_worlds':15*len(seeds),'planned_physical_worlds':len(jobs),
        'candidate_reselection':False,'dispatchable':False,'seed_usage_validated':False,'new_model_calls':0,'new_native_worlds':0})
