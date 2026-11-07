"""Environment observation QA; no package/server operation or real experiment."""
from copy import deepcopy
import json

import pytest

from scripts.reports import submission_environment as observer
from tests.reports.test_native_design_benchmark_plan import plan
from utopia.system.design_patch import digest


def version(name):
    if name in ('mlx','mlx-lm'):raise observer.metadata.PackageNotFoundError(name)
    return 'SCRIPTED-version'


def test_current_observation_never_claims_startup_or_separate_server_environment(tmp_path,monkeypatch):
    p=plan();before=deepcopy(p)
    monkeypatch.setattr(observer.subprocess,'check_output',lambda args,**kw:'a'*40 if 'rev-parse' in args else '')
    monkeypatch.setattr(observer.platform,'node',lambda:pytest.fail('must not collect hostname'))
    path=tmp_path/'requirements.txt';path.write_text('SCRIPTED test dependency only')
    r=observer.observe(p,tmp_path,package_version=version,observed_utc='SCRIPTED timestamp')
    assert p==before and r==observer.observe(p,tmp_path,package_version=version,observed_utc='SCRIPTED timestamp')
    assert r['startup_environment_attested'] is False and r['complete_environment_lock_claimed'] is False
    assert r['separate_model_server_packages_observed'] is False
    assert r['new_endpoint_requests']==r['new_inference_requests']==r['downloads']==r['package_installs']==0
    assert r['packages']['mlx']['version'] is None
    assert r['packages']['numpy']['version']=='SCRIPTED-version'
    assert r['content_sha256']==digest({k:v for k,v in r.items() if k!='content_sha256'})
    assert str(tmp_path) not in json.dumps(r) and '/Users/' not in json.dumps(r)


@pytest.mark.parametrize('revision,status',[('b'*40,''),('a'*40,' M utopia/simulation.py')])
def test_wrong_or_dirty_source_is_not_attested(tmp_path,monkeypatch,revision,status):
    monkeypatch.setattr(observer.subprocess,'check_output',lambda args,**kw:revision if 'rev-parse' in args else status)
    with pytest.raises(ValueError,match='clean exact'):
        observer.observe(plan(),tmp_path,package_version=lambda _:pytest.fail('check source first'))


def test_cli_never_writes_inside_frozen_source_raw_root_or_over_existing_file(tmp_path,monkeypatch):
    raw=tmp_path/'raw';raw.mkdir();source=tmp_path/'source';source.mkdir()
    p=raw/'plan.json';p.write_text(json.dumps(plan()))
    old=tmp_path/'old.json';old.write_text('keep')
    monkeypatch.setattr(observer,'observe',lambda *a,**kw:pytest.fail('reject before observation'))
    for output in [raw/'new.json',source/'new.json',old]:
        with pytest.raises(SystemExit):observer.main(['--plan',str(p),'--source-root',str(source),'--output',str(output)])
    assert old.read_text()=='keep'
