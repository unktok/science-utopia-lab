from copy import deepcopy
from dataclasses import replace
import json

import pytest

from utopia.optimization.native_causal_design import describe, FILENAME, OPTION
from utopia.optimization.native_file_workspace_v35 import file_catalog, read_file, write_file_operations
from utopia.optimization.native_design_space import require_candidate_in_space, validate_design_space
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.system import ScheduleSpec
from utopia.system.native_information_institution import information_system, information_design_space

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def anchor():
    return information_system(IMAGE)


def routing_domain(system, kind='code-and-graph'):
    domain = information_design_space(system, kind, fixed_production=True)
    return allow_review_routing(system, domain)


def test_native_actual_phase_order_is_not_the_review_routing_example_default():
    data = anchor().to_dict(); before = deepcopy(data)
    result = describe(data)
    assert result['status'] == 'declared-graph-valid' and data == before
    relation = result['review_decision_order'][0]
    assert (relation['review_phase'], relation['decision_phase']) == (90, 130)
    assert relation['decision_sender_after_review'] is True
    window = result['pre_review_windows'][0]
    assert (window['costs_phase'], window['review_phase']) == (80, 90)
    assert window['two_integer_phases_available'] is True
    assert result['new_model_calls'] == result['new_code_executions'] == 0
    assert describe(json.loads(json.dumps(data, sort_keys=True))) == result


def test_phase_facts_are_derived_again_after_a_schedule_edit():
    system = anchor()
    changed = replace(system, schedules=tuple(replace(s, phase=129)
        if s.mechanism_id == 'world.review' else s for s in system.schedules))
    result = describe(changed.to_dict())
    assert result['review_decision_order'][0]['review_phase'] == 129
    assert result['system_sha256'] != describe(system.to_dict())['system_sha256']


def test_invalid_draft_and_unknown_code_do_not_acquire_proven_semantics():
    data = anchor().to_dict(); data['connections'][0]['target_mechanism'] = 'absent'
    assert describe(data)['status'] == 'invalid-draft'
    data = anchor().to_dict()
    node = next(n for n in data['mechanisms'] if n['mechanism_id'] == 'world.selection')
    node['parameters']['code_artifact']['source'] = 'raise RuntimeError("DO_NOT_EXECUTE")'
    result = describe(data)
    assert result['status'] == 'declared-graph-valid'
    assert 'No authored Python' in result['boundaries'][0]


def test_opt_in_advice_is_a_current_read_only_virtual_file_not_a_repair():
    data = anchor().to_dict()
    assert FILENAME not in {f['filename'] for f in file_catalog(data)['files']}
    body = {OPTION: True}
    files = file_catalog(data, request=body)['files']
    assert next(f for f in files if f['filename'] == FILENAME)['read_only']
    result = json.loads(read_file(data, FILENAME, request=body)['content'])
    assert result == describe(data)
    with pytest.raises(ValueError): write_file_operations(data, FILENAME, '{}', request=body)
    data['connections'][0]['target_mechanism'] = 'absent'
    assert json.loads(read_file(data, FILENAME, request=body)['content'])['status'] == 'invalid-draft'


def test_unknown_scope_cannot_disable_production_checks():
    system = anchor(); domain = routing_domain(system)
    domain['world_law_scope'] = 'anything-goes'
    with pytest.raises(ValueError, match='unknown'):
        validate_design_space(system, domain)


def test_new_scope_still_forbids_changing_research_production_or_time():
    system = anchor(); domain = routing_domain(system)
    changed = replace(system, schedules=tuple(replace(s, phase=s.phase+1)
        if s.mechanism_id == 'world.research' else s for s in system.schedules))
    with pytest.raises(ValueError, match='schedule'):
        require_candidate_in_space(system, changed, domain)


@pytest.mark.parametrize('feedback', ['loss', 'matched-loss', 'technical-only'])
@pytest.mark.parametrize('enabled', [False, True])
def test_actual_campaign_request_binds_opt_in_context_and_preserves_resume(tmp_path, feedback, enabled):
    from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
    from utopia.optimization.native_benchmark_controls import objective_specs
    system = anchor()
    def campaign(flag):
        return NativeAdaptiveDesignCampaign(tmp_path/'campaign', initial_system=system,
            loss_spec=objective_specs()['efficiency'], seeds=[42], mode='blackbox',
            world_binding={'source_commit':'SCRIPTED','model_digest':'SCRIPTED','corpus_sha256':'SCRIPTED'},
            strategies={'local':{'kind':'SCRIPTED',OPTION:flag}}, proposal_feedback=feedback,
            design_space=routing_domain(system))
    first = campaign(enabled)
    request = first._request([], first._strategy_initial(), 1)
    assert request.get(OPTION, False) is enabled
    assert (OPTION in request) is enabled
    assert request['parent_system'] == system.to_dict()
    again = campaign(enabled)
    assert again._request([], again._strategy_initial(), 1) == request
    with pytest.raises(ValueError): campaign(not enabled)


def test_bounded_author_reads_advice_and_cold_replays_without_new_actions(tmp_path):
    from tests.optimization.test_native_authoring_ir import request, BINDING, IMAGE as TEST_IMAGE
    from tests.optimization.test_native_planning_author_v22 import PLAN
    from tests.optimization.test_native_staged_author_v15 import Model
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator, replay_staged_generation
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    body = request(); body[OPTION] = True
    model = Model([PLAN, {'tool':'read_file', 'filename':FILENAME},
        {'tool':'finish', 'rationale':'SCRIPTED explicit parent retention, not an improvement'}])
    generator = StagedVocabularyGenerator(model, tmp_path/'author', image_id=TEST_IMAGE,
        provider_binding=BINDING, max_steps=8, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    definition = generator(body)
    assert 'generation_failure' not in definition and len(model.calls) == 3
    assert FILENAME in model.calls[0]['prompt']
    directory = next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(directory) == definition
    assert generator(body) == definition and len(model.calls) == 3
    completed = json.loads((directory/'step-01.completed.json').read_text())
    assert completed['status'] == 'applied' and SCHEMA_NAME in json.dumps(completed)


SCHEMA_NAME = 'scienceutopia.native-causal-design.v1'


def test_read_only_cli_rebuilds_identically_and_refuses_overwrite(tmp_path, monkeypatch):
    from scripts.reports.native_causal_design_v1 import main
    system = tmp_path/'system.json'; system.write_text(json.dumps(anchor().to_dict()))
    outputs = [tmp_path/'one.json', tmp_path/'two.json']
    for output in outputs:
        monkeypatch.setattr('sys.argv', ['report', '--system',str(system),'--output',str(output)])
        main()
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    with pytest.raises(ValueError, match='fresh'): main()
