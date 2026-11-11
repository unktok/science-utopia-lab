"""Retained evidence bindings; local raw checks do not rerun experiments."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def test_retained_component_evidence_keeps_failed_and_unexercised_cases_separate():
    x=json.loads((ROOT/'research/results/native-component-lab-real-diagnostic-v1.json').read_text())
    assert x['actual_container_calls']==x['predeclared_container_calls']==3
    assert x['new_model_calls']==x['new_native_worlds']==0
    assert [r['status'] for r in x['results']]==['returned','returned','raised']
    assert x['results'][1]['historical_failure_exercised_here'] is False
    assert not x['model_self_debug_demonstrated'] and not x['whole_native_failure_reproduced']
    assert x['two_fresh_process_cold_replays']['exit_codes']==[0,0]
    assert re.fullmatch('[a-f0-9]{40}',x['source_commit'])
    def visit(v):
        if isinstance(v,dict):
            for k,value in v.items():
                if k.endswith('_sha256') and isinstance(value,str):assert re.fullmatch('[a-f0-9]{64}',value),(k,value)
                visit(value)
        elif isinstance(v,list):
            for value in v:visit(value)
    visit(x)
    raw=ROOT/x['output']/'summary.json'
    if raw.exists():
        assert hashlib.sha256(raw.read_bytes()).hexdigest()==x['raw_summary_file_sha256']
        actual=json.loads(raw.read_text())
        assert actual['content_sha256']==x['raw_summary_content_sha256']
        assert actual['source_commit']==x['source_commit']
        assert actual['cold_replay_sha256']==x['two_fresh_process_cold_replays']['matching_sha256']
        for retained,observed in zip(x['results'],actual['observations']):
            assert retained['status']==observed['status']
            assert retained['artifact_sha256']==observed['artifact_sha256']
            assert retained['result_content_sha256']==observed['result_content_sha256']


def test_retained_native_fixture_manifest_has_only_developer_input_provenance():
    p=ROOT/'research/data/native-component-fixtures-v1/summary.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest()=='e45b7810464fb8dd3ef51c7e5a9dc2553954a374fdbf68fe2b6763600095a2a3'
    x=json.loads(p.read_text())
    assert x['recorded_inputs']==x['unique_fixtures']==24
    assert x['node_counts']=={'native-feature-extractor':12,'world.selection':12}
    assert x['seeds']==[61001] and all(r['seed']==61001 for r in x['fixture_origins'])
    assert x['new_model_calls']==x['new_code_executions']==0
    assert x['designer_tool_connected'] is False
