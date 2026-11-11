"""Cold fixed-content accounting with scripted opinions, not scientific claims."""
from collections import Counter
from types import SimpleNamespace

import pytest

from scripts import run_native_common_content_readout_v1 as driver
from scripts.reports import native_common_content_readout_v1 as module
from tests.reports.test_native_common_content_readout_v1 import inputs
from tests.optimization.test_common_content_observer import Backend,PROVIDER
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest,clone


def seal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def fixture(tmp_path,monkeypatch):
    body=inputs();input_path=tmp_path/'inputs.json';save(input_path,{k:v for k,v in body.items() if k!='content_sha256'})
    order=list(driver.content_set(body));contract=make_contract(source_commit='a'*40,provider=PROVIDER,
        backend={**PROVIDER,'ollama_version':'SCRIPTED-version'},maximum_posts=228,critics=3)
    p={'schema':driver.SCHEMA+'.plan','source_commit':'a'*40,'preceding_report':str(tmp_path/'prior'),
        'inputs_path':str(input_path),'inputs_file_sha256':module.file_sha256(input_path),
        'inference_lock':str(tmp_path/'lock'),'contract':contract,'content_order':order,
        'initial_interface_check_content_hashes':order[:3]}
    root=tmp_path/'run';root.mkdir();p=save(root/'plan.json',p)
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr(driver,'wait_report',lambda directory:{'status':'closed'})
    backend=Backend();monkeypatch.setattr(driver,'LocalObserverBackend',lambda **kwargs:backend)
    driver.run(root);assert len(backend.calls)==228
    monkeypatch.setattr(module,'INPUT_SHA',module.file_sha256(input_path))
    return body,root,backend


def test_actual_observer_boundary_and_two_cold_exports_match_every_file(tmp_path,monkeypatch):
    body,root,backend=fixture(tmp_path,monkeypatch)
    for name in ('one','two'):module.export(SimpleNamespace(run=root,output=tmp_path/name))
    expected={'report.json','contents.csv','worlds.csv','manifest.json','fixed-content-ratings.png','fixed-content-ratings.svg'}
    assert {p.name for p in (tmp_path/'one').iterdir()}==expected
    assert all((tmp_path/'one'/n).read_bytes()==(tmp_path/'two'/n).read_bytes() for n in expected)
    report=driver.read(tmp_path/'one/report.json')
    assert report['physical_attempts']==228 and len(backend.calls)==228
    assert report['critic_rating_distribution']=={'4':228}
    assert report['content_panels_available']==76 and report['accepted_decision_records']==263
    assert sum(w['common_centered_utility_sum'] for w in report['world_rows'])==263
    assert not report['interpretation']['policy_reselection']


def test_unavailable_content_cannot_be_zero_filled_in_any_affected_world(tmp_path,monkeypatch):
    body,root,backend=fixture(tmp_path,monkeypatch);ratings=driver.read(root/'ratings.json');audit=driver.read(root/'audit.json')
    key=next(iter(ratings['ratings']));rating=ratings['ratings'][key]
    rating['ratings'][0]=None;rating.update(status='unavailable',mean_score=None);seal(ratings)
    report=module.summarize(body,ratings,audit)
    affected={r['physical_world'] for r in body['accepted_decisions'] if digest(r['content'])==key}
    assert report['content_panels_unavailable']==1
    for w in report['world_rows']:
        assert (w['common_centered_utility_sum'] is None)==(w['identity'] in affected)


def test_pooled_values_cannot_claim_measurements_unsupported_by_critic_positions(tmp_path,monkeypatch):
    body,root,backend=fixture(tmp_path,monkeypatch);ratings=driver.read(root/'ratings.json');audit=driver.read(root/'audit.json')
    next(iter(ratings['ratings'].values()))['mean_score']=5;seal(ratings)
    with pytest.raises(ValueError,match='pooling'):module.summarize(body,ratings,audit)


def test_closed_reader_rejects_literal_rating_change_even_with_resealed_derived_journal(tmp_path,monkeypatch):
    body,root,backend=fixture(tmp_path,monkeypatch);ratings=driver.read(root/'ratings.json')
    next(iter(ratings['ratings'].values()))['ratings'][0]['score']=5
    # A valid derivative checksum is not evidence that its score came from HTTP.
    (root/'ratings.json').unlink();save(root/'ratings.json',{k:v for k,v in ratings.items() if k!='content_sha256'})
    with pytest.raises(ValueError):module.export(SimpleNamespace(run=root,output=tmp_path/'no-report'))
    assert not (tmp_path/'no-report').exists() and len(backend.calls)==228
