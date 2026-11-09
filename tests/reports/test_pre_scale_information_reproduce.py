from copy import deepcopy
import json

import pytest

from scripts.reports.pre_scale_information_reproduce_v1 import DATA,validate,table_body
from utopia.system.design_patch import digest


def retained():return json.loads((DATA/'report.json').read_text())


def reseal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def test_all_retained_worlds_and_table_are_recomputed():
    report=validate(retained());body=table_body(report)
    assert len(report['rows'])==12 and len(report['paired_differences'])==9
    assert body.count('\\\\')==12
    assert '41011&M3&1&4&45&-1&18.5&3\\\\' in body


@pytest.mark.parametrize('part',['loss','mean','pair','missing','seed','year'])
def test_resealed_wrong_numbers_cannot_pass_retained_algebra(part):
    r=deepcopy(retained())
    if part=='loss':r['rows'][0]['scores']['throughput']=-100.
    if part=='mean':r['condition_loss_means']['M0']['efficiency']=-100.
    if part=='pair':r['paired_differences'][0]['loss_difference_from_disconnected']['efficiency']=0.
    if part=='missing':r['rows'].pop()
    if part=='seed':r['rows'][0]['seed']=42
    if part=='year':r['rows'][0]['first_direction_input_year']=True
    with pytest.raises(ValueError):validate(reseal(r))


def test_changed_payload_without_a_matching_hash_is_rejected():
    r=retained();r['rows'][0]['components']['A']=999
    with pytest.raises(ValueError):validate(r)
