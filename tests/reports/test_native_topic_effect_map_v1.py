"""Pure SCRIPTED six-slot projection; no plot, model, code or native world."""
from copy import deepcopy

import pytest

from scripts.reports import native_topic_effect_map_v1 as mapper
from scripts.reports.native_topic_free_readout_v1 import analyze
from tests.reports.test_native_topic_free_readout_v1 import fixture
from utopia.system.design_patch import digest


def report(*,null=None):
    p,a,records,observations=fixture(null=null);r=analyze(p,a,records,observations)
    requests=[]
    for i,w in enumerate(a['worlds']):
        # Repeated input hash does not imply matching response choices.
        q={'wire_requests':10,'completed_responses':10,'wire_inputs_without_committed_reply':0,
            'ordered_full_request_payload_sha256':'SCRIPTED-common-inputs',
            'ordered_literal_response_choices_sha256':'SCRIPTED-original-choices'if i%2==0 else'SCRIPTED-other-choices'}
        requests.append({'identity':w['identity'],'seed':42,'status':w['status'],'requests':q})
    r['behavior_evidence']={'world_request_sequences':requests}
    r['content_sha256']=digest(r);return r


def test_six_original_slots_and_relative_design_fields_remain_literal():
    raw=report();before=deepcopy(raw);v=mapper.derive(raw)
    assert len(v['rows'])==6 and raw==before
    for row,original in zip(v['rows'],raw['slots']):
        assert row['loss']==original['loss'] and row['status']==original['status']
        assert row['submitted_change']['changed_system_fields']==['metadata']
        assert row['matching_reference_inputs']==['core-only','core-plus-related']
        assert len(row['matching_reference_choices'])==1
    assert v['new_model_calls']==v['new_code_executions']==v['new_native_worlds']==0
    assert not v['loss_or_selection_changed']and not v['publication_ready']


@pytest.mark.parametrize('kind',['generation','runtime'])
def test_failed_or_unsubmitted_slot_never_receives_input_equivalence_or_zero_loss(kind):
    raw=report(null=kind);row=mapper.derive(raw)['rows'][0]
    assert row['loss']is None and row['delta_from_best_visible_reference']is None
    assert row['complete_input_trace']is None and row['matching_reference_inputs']is None
    if kind=='generation':assert row['recorded_requests']is None and row['submitted_change']is None
    else:assert row['recorded_requests']==10


@pytest.mark.parametrize('change',['order','missing-slot','duplicate-input','unmatched-prefix','wrong-status'])
def test_incomplete_or_misaligned_original_records_stop_instead_of_drawing_a_pass(change):
    raw=report()
    if change=='order':raw['slots'].reverse()
    elif change=='missing-slot':raw['slots'].pop()
    elif change=='duplicate-input':raw['behavior_evidence']['world_request_sequences']*=2
    elif change=='unmatched-prefix':raw['behavior_evidence']['world_request_sequences'][2]['requests']['wire_inputs_without_committed_reply']=1
    else:raw['behavior_evidence']['world_request_sequences'][2]['status']='failed'
    with pytest.raises(ValueError):mapper.derive(raw)


def test_reference_classes_do_not_join_different_native_seeds():
    raw=report();raw['behavior_evidence']['world_request_sequences'][2]['seed']=43
    row=mapper.derive(raw)['rows'][0]
    assert row['matching_reference_inputs']==[]and row['matching_reference_choices']==[]


def test_native_width_print_labels_keep_null_and_literal_id_legend_without_rendering():
    value=mapper.derive(report(null='runtime'));cells,legend=mapper.print_cells(value)
    assert len(cells)==6 and cells[0][-1]=='Unknown\nRetained null'
    assert 'No complete trace' in cells[0][2]
    assert all('Delta' in row[-1]for row in cells[1:])
    assert legend==[]  # This SCRIPTED case changes metadata, not mechanism IDs.
    value['rows'][1]['submitted_change']['source_nodes']=['SCRIPTED-original-id']
    cells,legend=mapper.print_cells(value)
    assert 'Source: m1' in cells[1][1]and legend==['m1 = SCRIPTED-original-id']
