"""Opt-in real-container public-path QA; HTTP/supervision are SCRIPTED.

Run only after real inference ends, from a clean pinned source. The source
must stay unchanged until pytest exits. This does not score a native world.
"""
import fcntl
import json
import os
from pathlib import Path

import pytest

from scripts.analyze_native_open_v7 import _inventory
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from utopia.optimization import native_bounded_staged_designer as bounded
from utopia.optimization import native_workflow_staged_designer_v1 as authoring
from utopia.optimization.native_component_lab_v1 import NativeComponentLab
from utopia.optimization.native_component_parameter_context_v1 import SCOPE, OPTION, parameters
from utopia.optimization.native_designer_tools_v25 import function_data
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_staged_author_v15 import PLAN_CONTROL
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_CURRENT_PARAMETER_PUBLIC_QA') != '1',
    reason='explicit clean-source window after actual inference required')
def test_actual_public_three_shapes_current_parameters_real_container_and_cold(tmp_path, monkeypatch):
    raw = Path(os.environ['SCIENCE_UTOPIA_CURRENT_PARAMETER_ASSAY_RUN']).resolve()
    plan = checked(json.loads((raw / 'plan.json').read_text()))
    terminal = checked(json.loads((raw / 'terminal.json').read_text()))
    assert plan['schema'] == 'scienceutopia.native-corrected-author-assay.v1.plan'
    assert terminal['status'] == 'closed' and terminal['completed_cases'] == 3
    source = pinned_revision(ROOT); before = _inventory(raw)
    provider = plan['provider']; bank = {k: clone(v) for k,v in plan['bank'].items() if k!='content_sha256'}
    bank[OPTION] = SCOPE; bank['content_sha256'] = digest(bank)
    original_plan = checked(json.loads((Path(plan['origin']) / 'plan.json').read_text()))
    attributed = authoring.require_bank(bank,
        {**original_plan['component_evidence'], 'parameter_context_scope':SCOPE}, original_plan['initial_system'])
    assert attributed == bank
    evidence = []
    with (raw / 'writer.lock').open('r') as original:
        fcntl.flock(original, fcntl.LOCK_SH | fcntl.LOCK_NB)
        for case in plan['cases']:
            location = tmp_path / case['label']; document = case['request']['parent_system']
            request = clone(case['request']); node = next(n for n in document['mechanisms']
                if n['mechanism_id'] == 'developer-catalog-agenda')
            artifact = node['parameters']['code_artifact']
            # Separate declared four-probe historical compatibility diagnostic.
            # It is not part of the author budget or a native scientific loss.
            executor = DockerCodeExecutor(image=provider['image_id'], timeout=15.)
            lab = NativeComponentLab(location / 'literal-parameter-diagnostic',
                records=bank['records'], provenance={'scope': 'Exact original recorded contexts; technical comparison only',
                    'original_assay_plan_sha256': plan['content_sha256']}, executor=executor,
                source_commit=source, maximum_probes=4)
            origins = sorted((o for o in bank['origins'] if o['node_id'] == node['mechanism_id']), key=lambda o:o['year'])
            assert len(origins) == 4
            literal = [lab.probe(artifact, 'fixture-' + o['bundle_sha256']) for o in origins]
            assert any(v['status'] == 'raised' and "KeyError: 'topic_priorities'" in v.get('error','') for v in literal)
            actions = [{'tool':'plan','objective_reasoning':'SCRIPTED public software QA, not optimization',
                'design_intent':'Prescribed unchanged algorithm plus comment; test current parameter projection'},
                {'tool':'write_file','filename':'code/developer-catalog-agenda.py',
                    'content':artifact['source'] + '\n# SCRIPTED parameter-context public native-document QA\n'},
                {'tool':'finish'}]
            class Session(ScriptedSession):
                calls=[]; production=[]
                def get(self, url, **kw):
                    return Response({'version':'SCRIPTED-current-parameter-QA'} if url.endswith('/version') else {
                        'models':[{'name':provider['model'],'digest':provider['model_digest']}]})
                def post(self, url, **kw):
                    payload = json.loads(kw['data']); system = payload['messages'][0]['content']
                    if 'TRUSTED INTERFACE CALIBRATION TASK' in system:
                        value = super().post(url, **kw).json(); value['model'] = provider['model']; return Response(value)
                    control = system.startswith('INSTRUCTED PLANNING INTERFACE CONTROL')
                    action = PLAN_CONTROL if control else actions[len(self.production)]
                    if not control: self.production.append(payload)
                    return Response({'model':provider['model'],'done':True,'done_reason':'stop',
                        'prompt_eval_count':120,'eval_count':12,'message':{'role':'assistant',
                            'content':json.dumps(function_data(action))}})
            monkeypatch.setattr('requests.Session', Session)
            monkeypatch.setattr('utopia.optimization.native_scientist_load_v38.load_local_role', lambda *a, **kw:None)
            def child(argv, **kw):
                bounded.worker(argv[-2], argv[-1]); return {'timed_out':False,'returncode':0}
            monkeypatch.setattr(bounded, 'run_bounded', child)
            backend = {'model':provider['model'],'model_digest':provider['model_digest'],
                'ollama_version':'SCRIPTED-current-parameter-QA'}
            designer = authoring.StagedWorkflowDesigner(location / 'public', provider=provider,
                backend=backend, inference_lock=location / 'SCRIPTED-inference.lock', source_commit=source, bank=bank)
            request = designer.feedback.declare_request(request)
            certificate = designer.calibrate(request)
            assert isinstance(certificate, Path) and certificate.is_file() and not Session.production
            result = designer.execute(request, purpose='proposal', certificate=certificate)
            assert 'generation_failure' not in result['definition'] and len(Session.production) == 3
            gen = designer.directory / ('proposal-'+digest(request)) / 'editor-session/authoring' / ('generation-'+digest(request))
            edited = checked(json.loads((gen / 'step-01.completed.json').read_text()))
            feedback = edited['transition']['result']['component_feedback']
            assert feedback['probe_attempts'] == 4
            assert all(v['status'] == 'returned' for t in feedback['tests'] for v in t['results'])
            assert all(v['context']['parameters'] == parameters(document, node['mechanism_id'])
                for v in edited['component_probe_records'])
            assert SCOPE in json.dumps(Session.production[-1])
            for purpose in ('calibration','proposal'):
                replayed = authoring.replay(designer.directory / (purpose+'-'+digest(request)), request=request,
                    provider=provider, backend=backend, source_commit=source, bank=bank, purpose=purpose)
                if purpose == 'proposal': assert replayed == result
            assert len(Session.production) == 3
            evidence.append({'label':case['label'],'actual_generic_controls':len(checked(json.loads(certificate.read_text()))['records']),
                'SCRIPTED_proposal_POSTs':3,'literal_historical_probe_statuses':[v['status'] for v in literal],
                'current_parameter_probe_statuses':[v['status'] for t in feedback['tests'] for v in t['results']],
                'actual_public_certificate_Path_and_paired_cold':True,'new_native_worlds':0,'actual_model_POSTs':0})
        assert before == _inventory(raw) and pinned_revision(ROOT) == source
    save(tmp_path / 'verification.json', {'schema':'scienceutopia.current-parameter-public-QA.v1',
        'source_commit':source,'original_assay_plan_file_sha256':file_sha256(raw / 'plan.json'),
        'original_raw_inventory_sha256':digest(before),'cases':evidence,
        'real_container_probes':24,'actual_model_POSTs':0,'new_native_worlds':0,
        'HTTP_and_process_supervision':'SCRIPTED','whole_native_world_verified':False,
        'real_new_source_model_calibration_verified':False,'publication_ready':False})
