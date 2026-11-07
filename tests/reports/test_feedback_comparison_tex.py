"""Literal manuscript projection QA; synthetic fixtures are not research."""
from copy import deepcopy
import json

import pytest

from scripts.analyze_native_feedback_comparison import summarize
from scripts.reports.feedback_comparison_tex import render,main
from tests.reports.test_native_feedback_comparison_analysis import fixtures
from utopia.system.design_patch import digest


def summary():
    p,runs,baseline=fixtures()
    for arm,run in runs.items():
        for row in run['observations']:
            row['loss']=row['cross_scores'][p['losses'][p['assignments'][arm]['objective']]['id']]
    return summarize(p,runs,baseline)


def rehash(value):
    value['content_sha256']=digest({k:v for k,v in value.items() if k!='content_sha256'})


def test_all_literal_rows_nulls_and_hash_caption_without_changing_input():
    value=summary(); before=deepcopy(value)
    text=render(value)
    assert value==before and '8 completed candidates' in text
    assert text.count(' & complete & ')==9
    assert value['content_sha256'] in text and '-10.000' in text
    row=value['candidate_rows'][0]
    row.update(status='technical-failure',loss=None,cross_scores={'throughput':None,'efficiency':None})
    rehash(value);text=render(value)
    assert '7 completed candidates' in text and '1 execution failures' in text
    assert r'execution failure & \textemdash & \textemdash' in text


@pytest.mark.parametrize('kind',['mismatch','missing','duplicate','bool','failure-number','generation','baseline'])
def test_render_rejects_changed_semantics_even_after_rehash(kind):
    value=summary();row=value['candidate_rows'][0]
    if kind=='mismatch':row['loss']=-999.
    if kind=='missing':value['candidate_rows'].pop()
    if kind=='duplicate':value['candidate_rows'][1]=deepcopy(row)
    if kind=='bool':row['cross_scores']['efficiency']=True
    if kind=='failure-number':row['status']='technical-failure'
    if kind=='generation':row['generation']=True
    if kind=='baseline':value['baseline']['row']['cross_scores']['throughput']=-123.
    rehash(value)
    with pytest.raises(ValueError):render(value)


def test_cli_never_overwrites_table_or_mutates_summary(tmp_path):
    value=summary();source=tmp_path/'SCRIPTED-summary.json';source.write_text(json.dumps(value))
    before=source.read_bytes();output=tmp_path/'table.tex'
    assert main(['--summary',str(source),'--output',str(output)])==0
    table=output.read_bytes()
    with pytest.raises(ValueError,match='fresh'):
        main(['--summary',str(source),'--output',str(output)])
    assert source.read_bytes()==before and output.read_bytes()==table
