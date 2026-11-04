import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts'
spec=importlib.util.spec_from_file_location('diagnose_staged_designer_v15',SCRIPTS/'diagnose_staged_designer_v15.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
sys.modules['diagnose_staged_designer_v15']=d
spec=importlib.util.spec_from_file_location('wire_diagnosis',SCRIPTS/'diagnose_staged_designer_wire_v15.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def test_wire_preserves_nested_object_order_while_canonical_hash_does_not():
    a={'format':{'properties':{'tool':{},'path':{},'text':{}}}}
    b={'format':{'properties':{'path':{},'text':{},'tool':{}}}}
    assert a==b and d.canonical(a)==d.canonical(b)
    assert w.wire_bytes(a)!=w.wire_bytes(b)
    assert list(json.loads(w.wire_bytes(a))['format']['properties'])==['tool','path','text']


def test_reconstruction_changes_only_order_and_not_original():
    original={'format':{'properties':{'path':{},'tool':{}}},'messages':[{'content':'unchanged bytes'}]}
    source={'properties':{'tool':{},'path':{}}}
    new=w.ordered_payload(original,source)
    assert new==original
    assert list(new['format']['properties'])==['tool','path']
    assert list(original['format']['properties'])==['path','tool']


def test_reconstruction_rejects_different_source_semantics():
    with pytest.raises(ValueError):w.ordered_payload({'format':{'type':'object'}},{'type':'string'})


def test_raw_body_survives_sorted_outer_plan_serialization():
    body=w.wire_bytes({'format':{'properties':{'z':{},'a':{}}}}).decode()
    saved=json.loads(json.dumps({'wire_request_utf8':body},sort_keys=True))
    assert saved['wire_request_utf8']==body
    assert list(json.loads(saved['wire_request_utf8'])['format']['properties'])==['z','a']
