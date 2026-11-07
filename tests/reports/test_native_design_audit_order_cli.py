"""Fresh-process adapter orchestration QA over tiny SCRIPTED Git repositories.

This is NOT the native auditor or scientific evidence. It tests source isolation,
immutable input handling, guard preservation and deterministic adapter receipts.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import audit_native_design_benchmark_order as adapter


FIXTURE = '''
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
def digest(v):
 return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sealed(v):
 return {**v,'content_sha256':digest(v)}
def build_plan(*,source,scientist,designer,runtime_seed,backend,seed_usage_sha256):
 return sealed({'schema':'SCRIPTED.order-adapter-fixture','source_commit':source,
  'scientist':scientist,'designer':designer,'runtime_seed_binding':runtime_seed,'backend':backend,
  'evaluation_seed_usage_sha256':seed_usage_sha256,
  'reference_systems':{'zeta':{},'alpha':{}},'campaign_bindings':{}})
spec=SimpleNamespace(SCHEMA='SCRIPTED.order-adapter-fixture',PROTOCOL='SCRIPTED-protocol',
 EVALUATION_SEEDS=[31001],build_plan=build_plan)
def selection_payload(root,plan,*,frozen_utc,campaign_loader):
 return sealed({'schema':spec.SCHEMA+'.selection','plan_sha256':plan['content_sha256'],
  'frozen_utc':frozen_utc,'selected':{'z-arm':{},'a-arm':{}},
  'ordered_reference_rows':list(plan['reference_systems'])})
def evaluation_jobs(plan,selection):
 return [{'job_id':'SCRIPTED-job','ordered_labels':list(plan['reference_systems'])+list(selection['selected'])}]
driver=SimpleNamespace(spec=spec,selection_payload=selection_payload,evaluation_jobs=evaluation_jobs)
'''

AUDITOR = '''
import hashlib,json,subprocess
from pathlib import Path
from scripts.frozen_fixture import spec,driver,digest,sealed
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(Path(p).read_text())
def _inventory(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
  for p in sorted(Path(root).rglob('*')) if p.is_file()}
def source_proofs(root,source,*,scripts,resources):
 names=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',source],text=True).splitlines()
 files={}
 for name in names:
  expected=subprocess.check_output(['git','-C',str(root),'show',source+':'+name])
  if (Path(root)/name).read_bytes()!=expected: raise ValueError('SCRIPTED source changed')
  files[name]=hashlib.sha256(expected).hexdigest()
 return {'status':'SCRIPTED-exact-source-fixture-only','files':files}
def replay_campaign(*a): raise AssertionError('SCRIPTED fixture has no campaigns')
def analyze(root,source):
 plan=read(root/'plan.json'); selection=read(root/'selection.json')
 if list(plan['reference_systems'])!=['zeta','alpha']: raise ValueError('SCRIPTED plan order differs')
 if list(selection['selected'])!=['z-arm','a-arm']: raise ValueError('SCRIPTED selection order differs')
 if read(root/'scientific-observation.json')!={'loss':1}: raise ValueError('SCRIPTED independent scientific guard retained')
 return sealed({'schema':spec.SCHEMA+'.audit','SCRIPTED':True,'source_commit':source,
  'original_body_completed':True,'new_model_calls':0,'new_code_executions':0})
'''


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def commit(root):
    git(root, 'init', '-q')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=SCRIPTED QA', '-c', 'user.email=scripted@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'SCRIPTED isolated fixture')
    return git(root, 'rev-parse', 'HEAD')


def fixture(tmp_path):
    analysis, source, raw = [tmp_path / name for name in ('analysis', 'frozen', 'raw')]
    for name in adapter.FILES:
        write(analysis / name, (adapter.ROOT / name).read_text())
    commit(analysis)
    write(source / 'scripts/__init__.py', '')
    write(source / 'scripts/frozen_fixture.py', FIXTURE)
    write(source / 'scripts/analyze_native_design_benchmark.py', AUDITOR)
    source_sha = commit(source)
    space = {}; exec(FIXTURE, space)
    usage = space['sealed']({'valid': True, 'seeds': [31001], 'errors': [], 'prior_matching_runs': []})
    p = space['build_plan'](source=source_sha, scientist={'SCRIPTED': True}, designer={'SCRIPTED': True},
        runtime_seed={'SCRIPTED': True}, backend={'SCRIPTED': True}, seed_usage_sha256=usage['content_sha256'])
    s = space['selection_payload'](raw, p, frozen_utc='SCRIPTED', campaign_loader=None)
    start = {'source_commit': source_sha, 'action': 'all', 'status': 'started',
             'started_utc': '2026-11-07T00:00:00+00:00'}
    values = {'plan.json': p, 'selection.json': s, 'evaluation-seed-usage.json': usage,
        'evaluation-plan.json': {'schema': space['spec'].SCHEMA + '.evaluation-plan',
            'selection_sha256': s['content_sha256'], 'jobs': space['evaluation_jobs'](p, s)},
        'writer.started.json': start,
        'writer.ended.json': {**start, 'status': 'exited', 'exit_code': 0,
                              'ended_utc': '2026-11-07T01:00:00+00:00'},
        'scientific-observation.json': {'loss': 1},
        'references/zeta/observation.json': {}, 'references/alpha/observation.json': {}}
    for name, value in values.items(): write(raw / name, json.dumps(value, sort_keys=True))
    return analysis, source, raw, source_sha


def run(analysis, source, raw, sha, output, *extra):
    env = {**os.environ, 'PYTHONPATH': str(analysis), 'HF_HUB_OFFLINE': '1',
           'TRANSFORMERS_OFFLINE': '1', 'CUDA_VISIBLE_DEVICES': ''}
    return subprocess.run([sys.executable, str(analysis / adapter.FILES[0]), '--run', str(raw),
        '--source-tree', str(source), '--expected-source', sha, '--output', str(output), *extra],
        cwd=analysis, env=env, text=True, capture_output=True, timeout=30)


def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_fresh_process_full_body_is_deterministic_readonly_and_provenance_explicit(tmp_path):
    analysis, source, raw, sha = fixture(tmp_path); before = inventory(raw)
    outputs = [tmp_path / 'audit-1.json', tmp_path / 'audit-2.json']
    for output in outputs:
        r = run(analysis, source, raw, sha, output); assert r.returncode == 0, r.stderr
    assert outputs[0].read_bytes() == outputs[1].read_bytes() and inventory(raw) == before
    result = json.loads(outputs[0].read_text())
    assert result['SCRIPTED'] and result['original_body_completed']
    assert result['analysis_adapter']['source_guards_removed'] is False
    assert result['analysis_adapter']['unmodified_frozen_CLI_claimed_to_pass'] is False
    assert result['analysis_adapter']['experiment_source_commit'] == sha
    assert git(source, 'status', '--porcelain') == git(analysis, 'status', '--porcelain') == ''
    r = run(analysis, source, raw, sha, outputs[0]); assert r.returncode != 0
    assert 'must be fresh' in r.stderr and outputs[0].read_bytes() == outputs[1].read_bytes()


@pytest.mark.parametrize('what', ['observation', 'jobs', 'source', 'live'])
def test_adapter_does_not_bypass_independent_guards_or_rewrite_inputs(tmp_path, what):
    analysis, source, raw, sha = fixture(tmp_path)
    if what == 'observation':
        write(raw / 'scientific-observation.json', '{"loss":999}')
    elif what == 'jobs':
        value = json.loads((raw / 'evaluation-plan.json').read_text())
        value['jobs'][0]['ordered_labels'].reverse()
        write(raw / 'evaluation-plan.json', json.dumps(value))
    elif what == 'source':
        write(source / 'scripts/frozen_fixture.py', FIXTURE + '\n# changed\n')
    else:
        # Preserve the start, and simulate a missing terminal record, not a rerun.
        (raw / 'writer.ended.json').rename(raw / 'SCRIPTED-ended-held-aside.json')
    before = inventory(raw); output = tmp_path / 'rejected.json'
    r = run(analysis, source, raw, sha, output)
    assert r.returncode != 0 and not output.exists() and inventory(raw) == before
    expected = {'observation': 'scientific guard retained', 'jobs': 'evaluation jobs differ',
                'source': 'clean exact source checkout', 'live': 'normal writer closure'}
    assert expected[what] in r.stderr


def test_live_component_mode_is_explicitly_not_a_full_audit(tmp_path):
    analysis, source, raw, sha = fixture(tmp_path)
    (raw / 'writer.ended.json').rename(raw / 'SCRIPTED-ended-held-aside.json')
    write(raw / 'scientific-observation.json', '{"loss":999}')  # Not read by component mode.
    output = tmp_path / 'component.json'
    r = run(analysis, source, raw, sha, output, '--check-order-only')
    assert r.returncode == 0, r.stderr
    result = json.loads(output.read_text())
    assert result['full_original_source_audit_completed'] is False
    assert result['status'] == 'closed-search-order-check-not-full-study-audit'
    assert result['physical_evaluation_jobs'] == 1
