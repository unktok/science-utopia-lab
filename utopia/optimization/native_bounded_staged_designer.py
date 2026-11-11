"""Whole-session deadline and durable pre-dispatch wire for the staged editor.

Only trusted orchestration runs on the host. Authored Python remains literal
data, checked/replayed by the existing editor and executed only in its sandbox.
An interrupted/unknown HTTP dispatch ends this session, never starts another.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
from pathlib import Path
import sys
import time

from .native_numeric_designer import save,checked
from .native_designer_preflight import runtime_binding,EXECUTION_SCOPE
from .native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.runtime.bounded_process import run_bounded
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256,decode_json

SCHEMA='scienceutopia.bounded-staged-designer.v1'


class CompletionUnknown(BaseException):
    """Bypass semantic-error recovery when a prior inference may still run."""


class DurableSession:
    def __init__(self,session,directory,*,maximum_posts):
        self.session=session;self.directory=Path(directory);self.maximum_posts=maximum_posts
        self.count=0

    def get(self,*args,**kwargs):
        return self.session.get(*args,**kwargs)

    def post(self,endpoint,**kwargs):
        if endpoint!='http://127.0.0.1:11434/api/chat' or self.count>=self.maximum_posts:
            raise ValueError('bounded staged inference endpoint/budget differs')
        wire=kwargs.get('data')
        if not isinstance(wire,bytes):
            raise ValueError('exact pre-serialized staged wire bytes required')
        index=self.count;self.count+=1
        intent=save(self.directory/f'dispatch-{index:03d}.intent.json',{
            'schema':SCHEMA+'.wire-intent','endpoint':endpoint,'wire_utf8':wire.decode('utf-8'),
            'timeout_seconds':list(kwargs['timeout']) if isinstance(kwargs['timeout'],tuple) else kwargs['timeout'],
            'headers':clone(kwargs.get('headers',{})),
            'started_utc':datetime.now(timezone.utc).isoformat(),'retries':0})
        begin=time.monotonic()
        try:
            response=self.session.post(endpoint,**kwargs)
        except Exception as error:
            save(self.directory/f'dispatch-{index:03d}.http.json',{'schema':SCHEMA+'.http',
                'intent_sha256':intent['content_sha256'],'elapsed_seconds':time.monotonic()-begin,
                'completion_unknown':True,'error_type':type(error).__name__,'error':str(error)})
            raise CompletionUnknown('staged HTTP completion unknown; no following dispatch') from error
        save(self.directory/f'dispatch-{index:03d}.http.json',{'schema':SCHEMA+'.http',
            'intent_sha256':intent['content_sha256'],'elapsed_seconds':time.monotonic()-begin,
            'http_status':response.status_code,'raw_http_response':response.text})
        # A non-final provider envelope may represent a still-running request.
        # Preserve it, but never ask the model again as a semantic repair.
        try:body=decode_json(response.text,strict=True,finite_floats=True)
        except (ValueError,TypeError):body=None
        if response.status_code==200 and (not isinstance(body,dict) or body.get('done') is not True):
            raise CompletionUnknown('non-final staged provider envelope; no following dispatch')
        return response


def worker(intent_path,result_path):
    from .native_designer_roles_v38 import make_local_role_bound_generator
    from .native_designer_preflight import run_calibration
    from .native_scientist_load_v38 import load_local_role
    from .native_jobs import pinned_revision
    intent=checked(json.loads(Path(intent_path).read_text()));root=Path(result_path).parent
    result={'schema':SCHEMA+'.worker','intent_sha256':intent['content_sha256']}
    begin=time.monotonic()
    try:
        if (intent['runtime']!=runtime_binding()
                or intent['source_commit']!=pinned_revision(Path(__file__).resolve().parents[2])):
            raise ValueError('bounded editor clean source/runtime changed')
        feedback=None
        if 'post_edit_component_bank' in intent:
            if intent['kind']!='proposal':raise ValueError('component execution is proposal-only')
            from .native_post_edit_feedback_v1 import NativePostEditFeedback
            from utopia.system.code_mechanisms import DockerCodeExecutor
            feedback=NativePostEditFeedback(intent['post_edit_component_bank'],
                executor=DockerCodeExecutor(image=intent['provider']['image_id'],timeout=15.),
                source_commit=intent['source_commit'],maximum_probes=8)
            if (intent['request'].get('strategy_provenance') or {}).get('post_edit_component_contract')!=feedback.contract:
                raise ValueError('bounded component bank differs from declared request contract')
        if feedback is None and (intent['request'].get('strategy_provenance') or {}).get('post_edit_component_contract') is not None:
            raise ValueError('declared component feedback has no configured bank; no role load or dispatch')
        load_local_role(root/'designer-load.json',provider=intent['provider'],role='designer',
                        purpose='bounded-staged-'+intent['kind'])
        wrap=lambda session:DurableSession(session,root/'wire',maximum_posts=intent['maximum_posts'])
        if intent['kind']=='calibration':
            cert=run_calibration(root/'calibration',request=intent['request'],provider=intent['provider'],
                source_commit=intent['source_commit'],scope=EXECUTION_SCOPE,
                conversation_profile=BOUNDED_AUTHORING,session_wrapper=wrap)
            result.update(passed=cert['all_controls_passed'],certificate_sha256=file_sha256(root/'calibration/certificate.json'))
        elif intent['kind']=='proposal':
            generator=make_local_role_bound_generator(root/'authoring',image_id=intent['provider']['image_id'],
                provider_binding=intent['provider'],max_steps=16,max_tokens=8192,
                preflight_certificate=intent['certificate'],readiness_scope=EXECUTION_SCOPE,
                conversation_profile=BOUNDED_AUTHORING,inference_lock=root/'worker-inference.lock',
                **({'edit_feedback':feedback} if feedback is not None else {}))
            generator.model.session=wrap(generator.model.session)
            definition=generator(intent['request'])
            result.update(definition=definition,submitted=definition is not None)
        else:raise ValueError('unknown trusted bounded editor task')
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error),
                      completion_unknown=isinstance(error,CompletionUnknown))
        from .native_component_lab_v1 import ComponentProbePending
        if isinstance(error,ComponentProbePending):result['component_probe_pending']=True
    result['elapsed_seconds']=time.monotonic()-begin
    save(result_path,result)


def execute(directory,*,kind,request,provider,source_commit,certificate=None,
            seconds=1200,maximum_posts=16,inference_lock=None,post_edit_bank=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    lock_path=Path(inference_lock) if inference_lock else root/'inference.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    core={'schema':SCHEMA+'.intent','kind':kind,'request':clone(request),'provider':clone(provider),
        'runtime':runtime_binding(),'source_commit':source_commit,'certificate':str(Path(certificate).resolve()) if certificate else None,
        'seconds':seconds,'maximum_posts':maximum_posts,'max_steps':16,'max_tokens':8192,
        'conversation_profile':BOUNDED_AUTHORING}
    if post_edit_bank is not None:
        if kind!='proposal':raise ValueError('component bank execution is proposal-only; readiness declares its contract')
        checked(post_edit_bank);core['post_edit_component_bank']=clone(post_edit_bank)
    if (kind not in ('calibration','proposal') or type(seconds) not in (int,float)
            or not 1<=seconds<=1800 or type(maximum_posts) is not int or not 1<=maximum_posts<=40):
        raise ValueError('finite trusted editor task/budget required')
    with (root/'writer.lock').open('a') as writer,lock_path.open('a') as inference:
        for handle in (writer,inference):fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'intent.json').exists():
            prior=checked(json.loads((root/'intent.json').read_text()))
            if prior!={**core,'content_sha256':digest(core)}:
                raise ValueError('bounded editor source/request/budget changed')
            return replay(root)
        intent=save(root/'intent.json',core)
        execution=run_bounded([sys.executable,'-m',__name__,'--worker',str(root/'intent.json'),
            str(root/'worker-result.json')],seconds=seconds,cwd=Path(__file__).resolve().parents[2])
        manifest={str(p.relative_to(root)):file_sha256(p) for p in sorted(root.rglob('*.json'))}
        result=save(root/'result.json',{'schema':SCHEMA+'.result','intent_sha256':intent['content_sha256'],
            'execution':execution,'files':manifest,'redispatch_allowed':False,
            'worker_result_exists':(root/'worker-result.json').exists()})
        return replay(root)


def replay(directory):
    root=Path(directory);intent=checked(json.loads((root/'intent.json').read_text()))
    result=checked(json.loads((root/'result.json').read_text()))
    if intent['runtime']!=runtime_binding() or result['intent_sha256']!=intent['content_sha256']:
        raise ValueError('bounded editor runtime/intent mismatch')
    actual={str(p.relative_to(root)):file_sha256(p) for p in sorted(root.rglob('*.json')) if p!=root/'result.json'}
    if actual!=result['files']:raise ValueError('bounded editor has changed or unaccounted JSON journals')
    for relative,identity in result['files'].items():
        if file_sha256(root/relative)!=identity:raise ValueError('bounded editor raw journal changed')
    if result['execution']['timed_out'] or not result['worker_result_exists']:
        raise CompletionUnknown('bounded editor worker ended without a known terminal response; no redispatch')
    response=checked(json.loads((root/'worker-result.json').read_text()))
    if response['intent_sha256']!=intent['content_sha256']:raise ValueError('worker intent mismatch')
    if response.get('completion_unknown'):raise CompletionUnknown(response['error'])
    if response.get('component_probe_pending'):
        from .native_component_lab_v1 import ComponentProbePending
        raise ComponentProbePending(response['error'])
    if response.get('error_type'):raise ValueError(response['error_type']+': '+response['error'])
    if intent['kind']=='proposal':
        from .native_staged_author_v15 import replay_staged_generation
        generation=root/'authoring'/('generation-'+digest(intent['request']))
        binding=json.loads((generation/'request.json').read_text())
        if (binding['settings']['max_steps']!=intent['max_steps']
                or binding['settings']['max_tokens']!=intent['max_tokens']
                or binding['settings']['conversation_profile']!=intent['conversation_profile']):
            raise ValueError('bounded staged settings differ from actual journal')
        component=binding['settings'].get('post_edit_component_tests')
        if 'post_edit_component_bank' in intent:
            if (component is None or component['bank_content_sha256']!=intent['post_edit_component_bank']['content_sha256']
                    or component['source_commit']!=intent['source_commit'] or component['maximum_probe_attempts']!=8):
                raise ValueError('bounded post-edit configuration differs from bank/source/budget')
        elif component is not None:raise ValueError('undeclared component tests in bounded worker')
        definition=replay_staged_generation(generation,
            expected_request=intent['request'],expected_provider_binding=intent['provider'])
        if definition!=response['definition']:raise ValueError('bounded staged definition differs from cold replay')
        return definition
    return response


class BoundedStagedDesigner:
    def __init__(self,directory,*,provider,source_commit,certificate,inference_lock,post_edit_bank=None):
        self.directory=Path(directory);self.provider=provider;self.source=source_commit
        self.certificate=certificate;self.lock=inference_lock
        self.post_edit_bank=clone(post_edit_bank)

    def __call__(self,request):
        return execute(self.directory/('generation-'+digest(request)),kind='proposal',request=request,
            provider=self.provider,source_commit=self.source,certificate=self.certificate,inference_lock=self.lock,
            **({'post_edit_bank':self.post_edit_bank} if self.post_edit_bank is not None else {}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',nargs=2,required=True)
    args=parser.parse_args();worker(*args.worker)
