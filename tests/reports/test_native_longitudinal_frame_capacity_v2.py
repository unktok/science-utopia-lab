"""Prospective one-field context change; never an actual model capacity result."""
import json
from types import SimpleNamespace

import pytest

from scripts import diagnose_native_longitudinal_frame_capacity_v1 as base
from scripts import diagnose_native_longitudinal_frame_capacity_v2 as v2
from tests.reports.test_native_longitudinal_frame_capacity_v1 import frame, response
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def test_exact_old_messages_and_all_other_payload_values_survive_context_derivation():
    f = frame(); old = json.loads(f['wire_utf8'])
    old['messages'][0]['content'] = 'literal example: {"num_ctx":40960}\\n研究者'
    f.update(wire_utf8=json.dumps(old,ensure_ascii=False))
    f['wire_sha256'] = digest(f['wire_utf8'])
    derived = v2.derived_frame(f); new = json.loads(derived['wire_utf8'])
    assert new['options']['num_ctx'] == 65536 and old['options']['num_ctx'] == 40960
    new['options']['num_ctx'] = 40960
    assert new == old
    assert derived['changed_fields'] == {'/options/num_ctx':[40960,65536]}
    assert derived['original_wire_sha256'] == f['wire_sha256']


def test_context_derivation_rejects_unexpected_original_profile():
    f = frame(); p = json.loads(f['wire_utf8']); p['options']['num_ctx'] = 65536
    f['wire_utf8'] = json.dumps(p)
    with pytest.raises(ValueError,match='old40k'): v2.derived_frame(f)


def test_only_bounded_designer_context_changes_not_other_profiles():
    from utopia.optimization.native_designer_decoding_v24 import decoding_contract
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_scientist_load_v38 import payload_for
    from tests.optimization.test_native_loaded_roles_v38 import bindings
    assert decoding_contract('staged-v15',conversation_profile=BOUNDED_AUTHORING)['sampling_options']['num_ctx']==65536
    for profile in ('hermes-function-history-v26','plain-function-direct-v43','plain-function-recovery-v44'):
        assert decoding_contract('staged-v15',conversation_profile=profile)['sampling_options']['num_ctx']==40960
    assert decoding_contract('one-shot-v14')['sampling_options']['num_ctx']==32768
    assert payload_for(bindings()['scientist'],role='scientist')['options']['num_ctx']==40960


def test_retained_offline_counts_are_not_backend_capacity_or_gain():
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    p=checked(json.loads((Path(__file__).resolve().parents[2]/'research/results/native-longitudinal-offline-token-counts-v1.json').read_text()))
    assert [r['local_template_tokens'] for r in p['rows']]==[37296,44320]
    assert all(not r['reservation_fits_requested_context'] and r['prospective_65536_context_would_fit'] for r in p['rows'])
    assert p['new_model_calls']==0 and not p['original_input_modified']
    for key in ('backend_token_counts_measured','backend_tokenizer_rendering_independently_verified',
                'real_readiness_proved','scientific_gain_claimed','publication_ready'):
        assert p[key] is False


def test_retained64k_scope_and_derived_preparation_are_not_backend_or_full_native_proof():
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    p=checked(json.loads((Path(__file__).resolve().parents[2]/'research/results/native-longitudinal-64k-preflight-prepared-v1.json').read_text()))
    assert p['source_commit']=='a5be8d3103854368a4bc6ba4c13eff7552e9dd15'
    assert p['scope_schema']=='scienceutopia.native-longitudinal-source-scope.v2'
    assert p['unchanged_native_files']==272 and len(p['declared_author_modules'])==5
    assert not p['files_silently_excluded'] and not p['legacy_guard_modified']
    assert p['actual_legacy_guard_rejected_prospective_optimizer']
    assert p['capacity_prepare_exit_code']==0 and p['same_literal_messages_and_other_payload_values']
    assert len(p['capacity_frames'])==2 and p['new_model_POSTs']==0
    assert all(f['changed_fields']=={'/options/num_ctx':[40960,65536]} for f in p['capacity_frames'])
    for key in ('capacity_started','new64k_native_cold_proof','real64k_backend_capacity_proved',
                'actual_request_readiness_proved','scientific_comparison_dispatched','scientific_gain_claimed','publication_ready'):
        assert p[key] is False


def test_shared_real_journal_worker_uses_v2_plan_and_actual_wire_context(tmp_path,monkeypatch):
    frames = [v2.derived_frame(frame(a)) for a in base.ARMS]; posted=[]
    p={'schema':v2.SCHEMA+'.plan','provider':{},'backend':{},'frames':frames}
    monkeypatch.setattr(base,'backend_binding',lambda *a,**kw:{})
    monkeypatch.setattr(base,'load_local_role',lambda *a,**kw:None)
    monkeypatch.setattr(base,'require_plan',lambda *a:(_ for _ in ()).throw(AssertionError('wrong v1 plan API')))
    class Session:
        def post(self,endpoint,**kw):
            assert kw['data']==frames[len(posted)]['wire_utf8'].encode()
            posted.append(kw['data'])
            return SimpleNamespace(status_code=200,text=response(count=44320)['raw_http_response'])
    monkeypatch.setattr('requests.Session',Session)
    base.worker(tmp_path,require_plan_fn=lambda root:p)
    ended=base.read(tmp_path/'worker-terminal.json')
    assert ended['schema']==v2.SCHEMA+'.worker-terminal' and len(posted)==2
    assert all(r['capacity']['context_tokens']==65536 for r in ended['results'])
    assert ended['two_literal_frames_supported']
    assert not ended['production_certificate_issued']


def test_bounded_parent_launches_actual_v2_module_not_dunder_main(tmp_path,monkeypatch):
    p={'schema':v2.SCHEMA+'.plan','content_sha256':'a'*64,'source_commit':'b'*40,'worker_wall_seconds':2100}
    monkeypatch.setattr(base,'require_resources',lambda root:{})
    def child(argv,**kw):
        assert argv[2]==v2.MODULE and kw['seconds']==2100
        save(tmp_path/'worker-terminal.json',{'schema':v2.SCHEMA+'.worker-terminal','status':'closed-diagnostic-only'})
        return {'returncode':0,'timed_out':False,'redispatched':False}
    monkeypatch.setattr(base,'run_bounded',child)
    base.run(tmp_path,tmp_path/'resources',require_plan_fn=lambda root:p,worker_module=v2.MODULE)
    assert base.read(tmp_path/'terminal.json')['schema']==v2.SCHEMA+'.terminal'
