"""SCRIPTED literal planner readout and closed continuation interfaces."""
from copy import deepcopy
import json

import pytest

from scripts.reports.native_parent_presentation_loop_v1 import first_planner_trace
from tests.optimization.test_native_authoring_ir import BINDING, IMAGE
from tests.optimization.test_native_bounded_author_context_v45 import Model
from tests.optimization.test_native_parent_evidence_v46 import body
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_parent_evidence_v46 import OPTION
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator


@pytest.mark.parametrize('literal', [False,True])
def test_first_plan_readout_records_supplied_source_and_literal_hypothesis(tmp_path, literal):
    request = body()
    if not literal: del request['strategy_provenance'][OPTION]
    actions = [{'tool':'plan','objective_reasoning':'SCRIPTED exact supplied objective',
                'design_intent':'SCRIPTED hypothesis, not actual effect'}, {'tool':'finish'}]
    model = Model(deepcopy(actions))
    generator = StagedVocabularyGenerator(model,tmp_path/'author',image_id=IMAGE,
        provider_binding=BINDING,max_steps=8,max_tokens=8192,conversation_profile=PROFILE)
    definition = generator(request)
    assert 'generation_failure' not in definition
    inner = next((tmp_path/'author').glob('generation-*'))
    steps = [json.loads(p.read_text()) for p in sorted(inner.glob('step-*.completed.json'))]
    trace = first_planner_trace(request,inner,steps)
    assert trace['literal_parent_included'] == literal
    assert trace['untrusted_first_plan']['design_intent'] == actions[0]['design_intent']
    assert trace['first_tool'] == 'plan' and not trace['reasoning_or_causal_effect_inferred']
    if literal: assert trace['planning_parent_evidence']['selected_observation']['loss'] == -18.
    else: assert trace['planning_parent_evidence'] is None
    changed = json.loads((inner/'step-00.started.json').read_text())
    view = json.loads(changed['prompt'])
    view['literal_current_system'] = None if literal else request['parent_system']
    changed['prompt'] = json.dumps(view)
    (inner/'step-00.started.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='first planner'):
        first_planner_trace(request,inner,steps)


def test_normal_finish_uses_new_schema_original_writer_and_cold_adapter(monkeypatch):
    from scripts import finish_native_parent_presentation_loop_v1 as finish
    calls = []
    monkeypatch.setattr(finish,'finish',lambda args,**kw:calls.append(kw))
    finish.run(object())
    assert calls[0]['plan_schema'] == 'scienceutopia.native-parent-presentation-loop.v1.plan'
    assert calls[0]['audit_module'] == 'scripts.audit_native_parent_presentation_loop_v1'
    assert calls[0]['writer_command'] == 'scripts.run_native_parent_presentation_loop_v1 run'


@pytest.mark.parametrize('kind,expected', [
    ('scores',()), ('choices',('--study','parent-presentation')),
    ('effects',('--scope','parent-presentation-development')), ('requests',())])
def test_each_reader_waits_for_normal_original_double_audit_cost_closure(tmp_path, monkeypatch, kind, expected):
    from types import SimpleNamespace
    from scripts import finish_native_parent_presentation_report_v1 as finish
    calls = []
    monkeypatch.setattr(finish,'finish',lambda args,**kw:calls.append(kw))
    finish.run(SimpleNamespace(kind=kind,frozen_source=tmp_path))
    assert calls[0]['preceding_schema'] == 'scienceutopia.native-parent-presentation-loop-finish.v1'
    assert calls[0]['report_extra_arguments'][-len(expected):] == expected if expected else True


def test_both_figures_retain_all_eight_reference_labels_and_twelve_slot_labels(tmp_path):
    from scripts.reports.native_parent_presentation_loop_v1 import render
    from scripts.run_native_parent_presentation_loop_v1 import ARM_ORDER
    from utopia.system.native_planning_controls import ORDER
    references = [{'label':name,'scores':{'throughput':-float(i),'content-utility':-float(i)/3}}
                  for i,name in enumerate(ORDER)]
    slots = [{'objective':o,'presentation':p,'generation':g,'loss':-float(g),
              'cross_scores':{'throughput':-float(g),'content-utility':-float(g)/3}}
             for o in ('throughput','content-utility') for p in ('control','literal') for g in range(3)]
    render({'schema':'SCRIPTED-render-only','slots':slots,'references':references,
            'score_order':['throughput','content-utility'],'arm_order':list(ARM_ORDER)},tmp_path)
    for name in ('objective-loss-paths.svg','objective-cross-scores.svg'):
        svg = (tmp_path/name).read_text()
        assert all('R'+str(i+1)+' = '+label in svg for i,label in enumerate(ORDER))
    svg = (tmp_path/'objective-cross-scores.svg').read_text()
    assert all(prefix+str(g) in svg for prefix in ('TC','TL','UC','UL') for g in range(3))
