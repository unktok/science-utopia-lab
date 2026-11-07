"""Match author-facing cardinality prose to the unchanged generic runtime."""
from dataclasses import replace
import json

import pytest

from tests.optimization.test_native_authoring_ir import request,BINDING
from utopia.optimization.native_authoring_ir import CODE_CONTRACT_LAYOUT
from utopia.optimization.native_staged_author_v15 import build_prompt,build_conversation,initial_draft,call_task
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.system import MechanismFamily,MechanismSpec,PortSpec,ChannelKind
from utopia.system.runtime import _validate_result,GraphRuntimeError,MechanismResult,MechanismValue


def test_required_vs_optional_empty_messages_match_exact_existing_runtime():
    node=MechanismSpec('qa-node',MechanismFamily.CUSTOM,'qa-handler',
        outputs=(PortSpec('result',ChannelKind.ARTIFACT,'qa-object',required=True),))
    for outputs in ({},{'result':[]}):
        with pytest.raises(GraphRuntimeError,match='did not emit required output'):
            _validate_result(node,MechanismResult(outputs=outputs))
    optional=replace(node,outputs=(replace(node.outputs[0],required=False),))
    assert _validate_result(optional,MechanismResult(outputs={'result':[]}))=={'result':()}
    value=MechanismValue(payload={'SCRIPTED':'object payload; no scientific decision'})
    assert _validate_result(node,MechanismResult(outputs={'result':[value]}))=={'result':(value,)}
    assert 'required=true must emit at least one message envelope' in CODE_CONTRACT_LAYOUT
    assert 'Optional output ports may emit []' in CODE_CONTRACT_LAYOUT
    assert 'not a requirement about which scientific decision' in CODE_CONTRACT_LAYOUT


def test_bounded_real_conversation_keeps_cardinality_rule_even_at_planning_turn():
    body=request()
    prompt=build_prompt(body,initial_draft(body),[],image_id=BINDING['image_id'],binding_sha256='d'*64,
        settings={'max_steps':16,'conversation_profile':BOUNDED_AUTHORING})
    messages=build_conversation(prompt,call_task(0,16,conversation_profile=BOUNDED_AUTHORING,prompt=prompt),
        native_tools=True,conversation_profile=BOUNDED_AUTHORING)
    assert 'required=true must emit at least one message envelope' in messages[0]['content']
    assert 'Optional output ports may emit []' in messages[0]['content']
    assert json.loads(prompt)['loss_arithmetic']['extra_eligibility_constraint'] is False
