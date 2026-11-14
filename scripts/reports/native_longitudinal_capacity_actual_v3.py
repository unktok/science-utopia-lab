"""Retain closed real two-frame capacity evidence, never a production certificate."""
import argparse
from pathlib import Path
import subprocess

from scripts.diagnose_native_longitudinal_frame_capacity_v1 import read, result_from_http
from scripts.diagnose_native_longitudinal_frame_capacity_v2 import derived_frame
from scripts.diagnose_native_longitudinal_frame_capacity_v1 import late_frames
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import decode_json, file_sha256


def export(root):
    root=Path(root).resolve();p=read(root/'plan.json');t=read(root/'terminal.json')
    w=read(root/'worker-terminal.json');load=read(root/'designer-load.json')
    assert p['schema']=='scienceutopia.longitudinal-late-frame-capacity.v3.plan'
    assert t['worker_terminal']==w and t['source_commit']==p['source_commit']
    assert t['execution']['returncode']==0 and not t['execution']['timed_out']
    assert w['status']=='closed-diagnostic-only' and not w['completion_unknown']
    assert load['valid_empty_prompt_load'] and load['http_status']==200
    _,original,_=late_frames(p['origin_run'],p['origin_audits'])
    assert p['frames']==[derived_frame(f) for f in original]
    assert len(list((root/'wire').glob('*.intent.json')))==2
    assert len(list((root/'wire').glob('*.http.json')))==2
    rows=[]
    for i,f in enumerate(p['frames']):
        intent=read(root/f'wire/dispatch-{i:03d}.intent.json')
        http=read(root/f'wire/dispatch-{i:03d}.http.json')
        assert intent['wire_utf8']==f['wire_utf8']
        actual=result_from_http(f,http);retained=read(root/f'frame-{i}.json')
        assert actual=={k:v for k,v in retained.items() if k!='content_sha256'}
        assert actual==w['results'][i] and actual['capacity_supported_for_this_literal_frame']
        body=decode_json(http['raw_http_response'],strict=True,finite_floats=True)
        rows.append({**actual,'provider_duration_seconds':{k:body[k]/1e9 for k in
            ('total_duration','load_duration','prompt_eval_duration','eval_duration')}})
    frozen=root.parents[1]
    assert subprocess.check_output(['git','-C',str(frozen),'rev-parse','HEAD'],text=True).strip()==p['source_commit']
    assert not subprocess.check_output(['git','-C',str(frozen),'status','--porcelain'],text=True).strip()
    assert not subprocess.check_output(['git','-C',str(frozen),'diff','a5be8d3103854368a4bc6ba4c13eff7552e9dd15',p['source_commit'],'--','utopia'],text=True)
    resource_files={}
    for path,sha in read(root/'started.json')['resource_files'].items():
        path=frozen/path
        assert file_sha256(path)==sha
        resource_files[str(path)]=sha
    return {'schema':'scienceutopia.native-longitudinal-actual-capacity-retained.v3',
        'source_commit':p['source_commit'],'run':str(root),'actual_session_id':39363,
        'actual_session_exit_code':0,'plan_content_sha256':p['content_sha256'],
        'source_utopia_literal_to_tested_scientific_source':True,
        'scientific_source':'a5be8d3103854368a4bc6ba4c13eff7552e9dd15',
        'old_250_percent_resource_failures_reclassified':False,
        'resource_contract':p['resource_contract'],'resource_files':resource_files,
        'files':{str(path):file_sha256(path) for path in sorted(root.rglob('*.json'))},
        'models':{'designer':p['provider']['model'],'digest':p['provider']['model_digest'],
                  'backend':p['backend']},
        'load_seconds':load['elapsed_seconds'],'worker_seconds':t['execution']['elapsed_seconds'],
        'actual_POSTs':{'empty_load':1,'capacity_chat':2,'total':3},'frames':rows,
        'shared_host_timing_not_dedicated_benchmark':True,
        'all_future_frames_capacity_proved':False,'backend_rendering_independently_verified':False,
        'production_certificate_issued':False,'actual_request_readiness_proved':False,
        'scientific_comparison_dispatched':False,'scientific_worlds':0,'returned_actions_executed':0,
        'scientific_gain_claimed':False,'publication_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    value=save(a.output,export(a.run));print(value['content_sha256'])
