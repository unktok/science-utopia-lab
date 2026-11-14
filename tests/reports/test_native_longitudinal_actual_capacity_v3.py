"""Retained actual capacity closure is narrow, not a scientific gain."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked


def test_two_actual_late_frames_complete_without_production_or_gain_claim():
    root=Path(__file__).resolve().parents[2]
    p=checked(json.loads((root/'research/results/native-longitudinal-actual-capacity-v3.json').read_text()))
    assert p['source_commit']=='7daa16656800d33f4fa28e2da1a2054ce779fc98'
    assert p['actual_session_id']==39363 and p['actual_session_exit_code']==0
    assert p['actual_POSTs']=={'empty_load':1,'capacity_chat':2,'total':3}
    assert p['source_utopia_literal_to_tested_scientific_source']
    assert [f['observed_prompt_tokens'] for f in p['frames']]==[37298,44322]
    assert [f['observed_output_tokens'] for f in p['frames']]==[669,539]
    for f in p['frames']:
        assert f['done'] and f['done_reason']=='stop' and f['http_status']==200
        assert f['capacity_supported_for_this_literal_frame'] and not f['returned_action_executed']
        assert f['capacity']['observed_prompt_eval_count']+8192<=65536
    for k in ('old_250_percent_resource_failures_reclassified','all_future_frames_capacity_proved',
              'backend_rendering_independently_verified','production_certificate_issued',
              'actual_request_readiness_proved','scientific_comparison_dispatched',
              'scientific_gain_claimed','publication_ready'):
        assert p[k] is False
    assert p['scientific_worlds']==p['returned_actions_executed']==0
