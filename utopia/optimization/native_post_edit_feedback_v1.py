"""Opt-in, non-veto component feedback after literal code-artifact edits.

All source edits remain applied, including failed tests. No baseline output,
policy novelty or fixture compatibility is a condition for explicit finish.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from utopia.optimization.native_component_lab_v1 import (NativeComponentLab,ComponentProbePending,fixture_bank,
    validate_probe_budget,LEGACY_PROBE_SCOPE)
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.code_mechanisms import sha,validate_code_artifact
from utopia.system.design_patch import clone,digest

SCHEMA='scienceutopia.native-post-edit-feedback.v1'
OPTION='post_edit_component_contract'
NOTE=('OPTIONAL COMPONENT TESTS ARE DECLARED FOR THIS SESSION. After a changed '
    'eligible code artifact, the orchestrator tests its literal source in a no-network '
    'container on the configured recorded inputs. Tests do not run on the host, '
    'change code, revert an edit, supply a baseline policy, change the loss, or veto '
    'finish. Read returned errors and explicitly author any repair yourself. '
    'Passing a fixture does not certify another input or the whole native world. '
    'Unconfigured/new interfaces remain allowed. All tests use the declared finite '
    'probe budget; once exhausted, subsequent edits are retained but untested. ')


def code_nodes(document):
    values={}
    nodes=document.get('mechanisms',[]) if isinstance(document,dict) else []
    for n in nodes if isinstance(nodes,list) else []:
        if not isinstance(n,dict) or not isinstance(n.get('mechanism_id'),str):continue
        params=n.get('parameters');artifact=params.get('code_artifact') if isinstance(params,dict) else None
        if artifact is not None:values.setdefault(n['mechanism_id'],[]).append(clone(artifact))
    return values


def consumed(steps):
    total=0
    for step in steps or []:
        transition=step.get('transition') or {};result=transition.get('result') or {}
        feedback=result.get('component_feedback') if isinstance(result,dict) else None
        if feedback is not None:
            if feedback['probe_offset']!=total:raise ValueError('post-edit probe prefix differs')
            total+=feedback['probe_attempts']
    return total


def persistent_diagnostics(document,steps):
    """Retain code-version-specific test observations across unrelated reads.

    This is a compact projection of existing records, never another probe or
    a finish gate. A later untested edit must not inherit an older pass/fail.
    Full error/context bodies remain in the exact read-only step archive.
    """
    latest={};tested={};by_artifact={}
    for index,step in enumerate(steps):
        transition=step.get('transition')
        if not isinstance(transition,dict):continue
        result=transition.get('result')
        feedback=result.get('component_feedback') if isinstance(result,dict) else None
        if not isinstance(feedback,dict):continue
        for ordinal,test in enumerate(feedback.get('tests',[])):
            node=test['node_id'];entry={'step':step['step'],'status':test['status'],
                'artifact_sha256':test.get('artifact_sha256'),
                'exact_archive_filename':f'archive/steps/{index:02d}.json',
                'json_pointer':f'/transition/result/component_feedback/tests/{ordinal}',
                'test_value_sha256':digest(test),
                'validation_error_type':test.get('error_type'),
                'validation_error_excerpt':test['error'][:256] if isinstance(test.get('error'),str) else None,
                'results':[{k:clone(value[k]) for k in
                    ('fixture_id','status','error_type','full_error_sha256','reply_content_sha256','result_sha256')}
                    | {'error_excerpt':None if value['error_excerpt'] is None else value['error_excerpt'][:256],
                       'display_excerpt_is_partial':value.get('error_is_excerpt',False) or (
                           value['error_excerpt'] is not None and len(value['error_excerpt'])>256),
                       'display_excerpt_limit_characters':256}
                    | ({'tensor_delivery_diagnostic':clone(value['tensor_delivery_diagnostic']),
                        'diagnostic_document_applicability':('same-current-document'
                            if value['tensor_delivery_diagnostic']['document_sha256']==digest(document)
                            else 'different-document-not-current-consumer-proof')}
                        if 'tensor_delivery_diagnostic' in value else {})
                    | ({'project_delivery_diagnostic':clone(value['project_delivery_diagnostic']),
                        'project_diagnostic_document_applicability':('same-current-document'
                            if value['project_delivery_diagnostic']['document_sha256']==digest(document)
                            else 'different-document-not-current-consumer-proof')}
                        if 'project_delivery_diagnostic' in value else {})
                    for value in test['results']]}
            latest[node]=entry
            if test['status']=='tested':
                tested[node]=entry
                by_artifact[node,test['artifact_sha256']]=entry
    current=code_nodes(document);rows=[]
    for node,notice in sorted(latest.items()):
        artifacts=current.get(node,[])
        current_hash=sha(artifacts[0]) if len(artifacts)==1 else None
        last=tested.get(node)
        applicable=by_artifact.get((node,current_hash))
        applicability=('code-artifact-not-present' if node not in current else
            'no-unique-current-artifact' if current_hash is None else
            'same-current-artifact' if applicable is not None else
            'current-artifact-untested')
        rows.append({'node_id':node,'current_artifact_sha256':current_hash,
            'test_applicability':applicability,'latest_component_notice':{k:v for k,v in notice.items() if k!='results'},
            'current_artifact_observed_suite':applicable,'most_recent_executed_suite':last})
    return {'schema':SCHEMA+'.persistent-observations.v1','components':rows,
        'scope':'Observed developer-fixture results tied to literal artifact hashes. '
            'An old suite is not a result for later untested code or the native trajectory.',
        'new_probe_attempts':0,'source_repair':False,'veto_on_finish':False}


class NativePostEditFeedback:
    def __init__(self,bank,*,executor,source_commit,maximum_probes=8):
        checked(bank);fixture_bank(bank['records'])
        self.probe_scope=bank.get('post_edit_probe_scope',LEGACY_PROBE_SCOPE)
        validate_probe_budget(maximum_probes,self.probe_scope)
        reference=bank.get('post_edit_reference','open-seed')
        if (not isinstance(reference,str) or not reference or
                ('post_edit_reference' in bank and reference not in bank.get('references',[]))):
            raise ValueError('explicit actual developer fixture reference required')
        self.bank=clone(bank);self.executor=executor;self.source_commit=source_commit
        self.tensor_delivery_scope=None
        self.project_delivery_scope=None
        if 'post_edit_project_delivery_scope' in bank:
            from .native_project_delivery_diagnostics_v1 import SCOPE
            if bank['post_edit_project_delivery_scope']!=SCOPE:
                raise ValueError('unknown explicit project-delivery diagnostic scope')
            self.project_delivery_scope=SCOPE
        if 'post_edit_tensor_delivery_scope' in bank:
            from .native_tensor_delivery_diagnostics_v1 import SCOPE
            if bank['post_edit_tensor_delivery_scope']!=SCOPE:
                raise ValueError('unknown explicit tensor-delivery diagnostic scope')
            self.tensor_delivery_scope=SCOPE
        self.maximum_probes=maximum_probes;self.suites={}
        for node in bank['nodes']:
            origins=[o for o in bank['origins'] if o['node_id']==node and o['reference']==reference]
            origins.sort(key=lambda o:o['year'])
            ids=['fixture-'+o['bundle_sha256'] for o in origins]
            if not ids or len(ids)>4 or len(set(ids))!=len(ids):
                raise ValueError('fixed nonempty at-most-four native contexts per component required')
            self.suites[node]=ids
        self.contract={'schema':SCHEMA,'bank_content_sha256':bank['content_sha256'],
            'source_commit':source_commit,'maximum_probe_attempts':maximum_probes,
            'image_id':executor.image_id,'executor_timeout_seconds':executor.timeout,
            'suites':clone(self.suites),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'fixture_summary':[{'fixture_id':'fixture-'+o['bundle_sha256'],'node_id':o['node_id'],
                'year':o['year'],'reference':o['reference']} for o in bank['origins'] if o['reference']==reference],
            'lab_source_sha256':hashlib.sha256(Path(__file__).with_name('native_component_lab_v1.py').read_bytes()).hexdigest(),
            'veto_on_test_failure':False,'source_repair':False,'new_native_worlds':0,'new_model_calls':0}
        if 'post_edit_reference' in bank:self.contract['fixture_reference']=reference
        if self.probe_scope!=LEGACY_PROBE_SCOPE:self.contract['budget_scope']=self.probe_scope
        if self.tensor_delivery_scope is not None:
            from .native_tensor_delivery_diagnostics_v1 import source_hashes,NOTE as DELIVERY_NOTE
            self.contract['tensor_delivery_diagnostics']={'scope':self.tensor_delivery_scope,
                'source_sha256':source_hashes(),'note':DELIVERY_NOTE,'veto_on_finish':False,
                'new_model_calls':0,'new_native_worlds':0,'new_tensor_body_executions':0}
        if self.project_delivery_scope is not None:
            from .native_project_delivery_diagnostics_v1 import source_hashes,NOTE as PROJECT_NOTE
            self.contract['project_delivery_diagnostics']={'scope':self.project_delivery_scope,
                'source_sha256':source_hashes(),'note':PROJECT_NOTE,'veto_on_finish':False,
                'new_model_calls':0,'new_native_worlds':0,'new_source_executions':0}

    def declare_request(self,request):
        result=clone(request)
        result.setdefault('strategy_provenance',{})[OPTION]=clone(self.contract)
        return result

    def bind(self,directory,*,read_only=False):
        directory=Path(directory);bank_path=directory/'edit-feedback-bank.json'
        if bank_path.exists():
            if checked(json.loads(bank_path.read_text()))!=self.bank:raise ValueError('post-edit fixture bank changed')
        elif read_only:raise ValueError('cold replay requires retained post-edit bank')
        else:save(bank_path,{k:v for k,v in self.bank.items() if k!='content_sha256'})
        lab_path=directory/'component-lab'
        if read_only and not (lab_path/'contract.json').exists():raise ValueError('cold replay requires component contract')
        lab=NativeComponentLab(lab_path,records=self.bank['records'],
            provenance={'scope':'post-edit developer component diagnostics, not native loss',
                'bank_content_sha256':self.bank['content_sha256']},executor=self.executor,
            source_commit=self.source_commit,maximum_probes=self.maximum_probes,budget_scope=self.probe_scope)
        return BoundFeedback(self,lab)

    @classmethod
    def cold(cls,directory,contract):
        bank=checked(json.loads((Path(directory)/'edit-feedback-bank.json').read_text()))
        def no_execution(*args):raise AssertionError('cold post-edit replay must not execute code')
        value=cls(bank,executor=SimpleNamespace(image_id=contract['image_id'],
            timeout=contract['executor_timeout_seconds'],execute=no_execution),
            source_commit=contract['source_commit'],maximum_probes=contract['maximum_probe_attempts'])
        if value.contract!=contract:raise ValueError('post-edit source/configuration differs during cold replay')
        return value


class BoundFeedback:
    def __init__(self,owner,lab):self.owner,self.lab=owner,lab

    def check_prefix(self,steps):
        rows=self.lab.replay()
        if len(rows)!=consumed(steps) or any(r['terminal'] is None for r in rows):
            raise ComponentProbePending('unaccounted or pending component feedback; no next model call')

    def raw_records(self,receipt):
        feedback=(receipt.get('result') or {}).get('component_feedback')
        if feedback is None:return []
        start=feedback['probe_offset'];end=start+feedback['probe_attempts'];rows=self.lab.replay()
        if end>len(rows):raise ValueError('missing exact post-edit probe records')
        return [{**clone(r),'context':clone(self.lab.fixtures[r['intent']['fixture_id']]['context']),
            'context_scope':'fixed developer fixture, not a new candidate native trajectory'} for r in rows[start:end]]

    def enrich(self,before,after,receipt,*,steps,dispatch):
        if not receipt['ok'] or receipt['tool'] not in ('edit','write_file','edit_fields','splice'):return receipt
        old,new=code_nodes(before['document']),code_nodes(after['document'])
        changed=[n for n in sorted(new) if new[n]!=old.get(n)]
        if not changed:return receipt
        offset=consumed(steps);cursor=offset;tests=[]
        if dispatch:self.check_prefix(steps)
        rows=self.lab.replay()
        for node in changed:
            entry={'node_id':node,'status':'not-configured','results':[]};tests.append(entry)
            if node not in self.owner.suites:continue
            if len(new[node])!=1:entry['status']='ambiguous-current-node';continue
            artifact=new[node][0]
            try:validate_code_artifact(artifact)
            except Exception as error:
                entry.update(status='incomplete-artifact',error_type=type(error).__name__,error=str(error));continue
            suite=self.owner.suites[node]
            if cursor+len(suite)>self.owner.maximum_probes:
                entry['status']='not-run-budget-exhausted';continue
            entry.update(status='tested',artifact_sha256=sha(artifact))
            for fixture in suite:
                if dispatch:
                    try:self.lab.probe(artifact,fixture)
                    except ComponentProbePending:raise
                    except BaseException as error:
                        # I/O or orchestration failure is not a model's invalid
                        # response. Stop before any further model/probe call.
                        raise ComponentProbePending('component orchestration failed; preserve intent') from error
                    rows=self.lab.replay()
                if cursor>=len(rows) or rows[cursor]['terminal'] is None:
                    raise ValueError('post-edit component reply is missing; never fabricate one')
                row=rows[cursor]
                if row['intent']['artifact']!=artifact or row['intent']['fixture_id']!=fixture:
                    raise ValueError('post-edit component call differs from current literal artifact/suite')
                reply=row['terminal'];full_error=reply.get('error')
                entry['results'].append({'fixture_id':fixture,'status':reply['status'],
                    'reply_content_sha256':reply['content_sha256'],'error_type':reply.get('error_type'),
                    'error_excerpt':None if full_error is None else full_error[:1024],
                    'error_is_excerpt':False if full_error is None else len(full_error)>1024,
                    'full_error_sha256':None if full_error is None else digest(full_error),
                    'result_sha256':sha(reply['result']) if reply['status']=='returned' else None,
                    'exact_step_probe_pointer':f'/component_probe_records/{cursor-offset}'})
                if self.owner.tensor_delivery_scope is not None and reply['status']=='returned':
                    from .native_tensor_delivery_diagnostics_v1 import diagnose
                    entry['results'][-1]['tensor_delivery_diagnostic']=diagnose(after['document'],node,reply['result'])
                if self.owner.project_delivery_scope is not None and reply['status']=='returned':
                    from .native_project_delivery_diagnostics_v1 import diagnose
                    entry['results'][-1]['project_delivery_diagnostic']=diagnose(
                        after['document'],node,reply['result'],self.lab.fixtures[fixture]['context'])
                cursor+=1
        result=clone(receipt)
        result['result']['component_feedback']={'schema':SCHEMA,'probe_offset':offset,
            'probe_attempts':cursor-offset,'remaining_probe_attempts':self.owner.maximum_probes-cursor,
            'bank_content_sha256':self.owner.bank['content_sha256'],'tests':tests,
            'veto_on_test_failure':False,'source_repair':False,'new_native_worlds':0,'new_model_calls':0}
        return result
