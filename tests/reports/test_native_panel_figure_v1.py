"""Synthetic physical-join guards for a fixed-record sensitivity graphic."""
from copy import deepcopy

import pytest

from scripts.figures.native_panel_sensitivity_v1 import selected_rows
from utopia.system.design_patch import digest


def seal(value):return {**value,'content_sha256':digest(value)}


def fixture():
    logical=[];worlds=[]
    for seed in (51001,51011,51017):
        for i,label in enumerate(('reference:reviewed-accept-all','selected:efficiency:parameters')):
            job=f'SCRIPTED-{seed}-{i}'
            logical.append({'label':label,'seed':seed,'physical_job':job})
            worlds.append({'identity':job,'seed':seed,'role':'selection-fixed-evaluation',
                'original_Q':3,'conditional_one_review_readout_Q_range':[1,5]})
    audit=seal({'logical_evaluation':logical,'plan_sha256':'a'*64,'source_commit':'b'*40})
    report=seal({'schema':'scienceutopia.fixed-record-panel-sensitivity.v1',
        'input_full_audit_content_sha256':audit['content_sha256'],'plan_sha256':'a'*64,
        'source_commit':'b'*40,'worlds':worlds})
    return report,audit


def test_six_display_rows_use_exact_old_evaluation_policies_and_seeds():
    r,a=fixture();original=deepcopy((r,a));rows=selected_rows(r,a)
    assert len(rows)==6 and (r,a)==original
    assert [row['seed'] for row in rows]==[51001,51001,51011,51011,51017,51017]


@pytest.mark.parametrize('issue',['missing-world','wrong-seed','bad-range','duplicated-label'])
def test_readout_cannot_be_joined_to_another_or_unavailable_world(issue):
    r,a=fixture()
    if issue=='missing-world':r['worlds'].pop()
    if issue=='wrong-seed':r['worlds'][0]['seed']=62001
    if issue=='bad-range':r['worlds'][0]['original_Q']=6
    if issue=='duplicated-label':
        a['logical_evaluation'].append(deepcopy(a['logical_evaluation'][0]))
        a={k:v for k,v in a.items() if k!='content_sha256'};a=seal(a)
        r['input_full_audit_content_sha256']=a['content_sha256']
    r=seal({k:v for k,v in r.items() if k!='content_sha256'})
    with pytest.raises(ValueError):selected_rows(r,a)
