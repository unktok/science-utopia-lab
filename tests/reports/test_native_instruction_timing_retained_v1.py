import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/native-instruction-timing-v1'


def test_literal_control_bytes_and_original_source_identity():
    r=checked(json.loads((ROOT/'research/results/native-instruction-timing-closed-verification-v1.json').read_text()))
    for name,expected in r['retained_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
    assert r['scientific_source_commit']=='5925d5b7d77bf7f13406730420022986e3fdac1f'
    assert r['physical_worlds']==3 and r['seed']==61001 and not r['policy_selection']
    assert not r['instruction_effectiveness_demonstrated'] and not r['publication_ready']


def test_delivery_not_equal_effect_and_complete_inputs_not_equal_topics():
    s=checked(json.loads((DATA/'summary.json').read_text()))
    assert [w['condition'] for w in s['worlds']]==['cut','early','late']
    assert [w['direction_requests_with_literal_instruction'] for w in s['worlds']]==[0,10,5]
    assert [w['stored_instruction_records'] for w in s['worlds']]==[0,5,5]
    for w in s['worlds']:
        assert w['scores']=={'throughput':-7.,'content-utility':-4.}
        assert w['shortest_displayed_selected_attempts']==4 and w['direction_request_attempts']==10
        assert w['mean_catalog_duration_on_known_attempts']==2.6
    chosen={condition:[(r['year'],r['selected_topic'],r['selected_catalog_duration_years'])
        for r in s['decisions'] if r['condition']==condition] for condition in ['cut','early','late']}
    assert chosen['cut']==chosen['early']==chosen['late']
    requests=checked(json.loads((DATA/'requests.json').read_text()))
    assert len(requests['complete_observed_input_classes'])==3
    assert len({w['requests']['ordered_literal_response_choices_sha256'] for w in requests['worlds']})==3


def test_original_cost_usage_is_physical_not_duplicate_interpretations():
    c=checked(json.loads((DATA/'costs.json').read_text()))
    assert c['scientist']['completed_responses']==389
    assert c['scientist']['provider_usage']['prompt_tokens']['recorded_sum']==360734
    assert c['scientist']['provider_usage']['completion_tokens']['recorded_sum']==38542
    assert c['common_content_observer']['physical_requests']==39
