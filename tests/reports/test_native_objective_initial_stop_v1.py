"""The specific stopped prefix must never be reclassified as normal closure."""
import pytest

from scripts.audit_native_objective_initial_stop_v1 import require_initial_stop,ERROR


@pytest.mark.parametrize('change',[None,'closed','wrong-stage','missing-reference','different-error','different-plan'])
def test_specific_stop_boundary_is_explicit(change):
    p={'schema':'scienceutopia.native-objective-instrument-loop.v1.plan','content_sha256':'a'*64}
    start={'schema':'scienceutopia.native-objective-instrument-loop.v1.start','plan_sha256':p['content_sha256']}
    end={'schema':'scienceutopia.native-objective-instrument-loop.v1.terminal','status':'stopped','stage':'optimization',
        'complete_references':5,'error_type':'ValueError','error':ERROR}
    if change=='closed':end['status']='closed'
    elif change=='wrong-stage':end['stage']='references'
    elif change=='missing-reference':end['complete_references']=4
    elif change=='different-error':end['error']='a different failure'
    elif change=='different-plan':start['plan_sha256']='b'*64
    if change:
        with pytest.raises(ValueError):require_initial_stop(p,start,end)
    else:require_initial_stop(p,start,end)
