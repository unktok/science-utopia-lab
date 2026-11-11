"""Explicit pointer attribution, never a positional or source-hash node guess."""
from scripts.reports.native_tensor_delivery_readout_v1 import probe_owners


def step(tests):return {'transition':{'result':{'component_feedback':{'tests':tests}}}}
def test(node,pointers):return {'node_id':node,'results':[{'exact_step_probe_pointer':p} for p in pointers]}


def test_explicit_reordered_nonconsecutive_ownership_and_ambiguity_are_retained():
    a=step([test('second',['/component_probe_records/3']),test('first',['/component_probe_records/0']),
        test('other',['/component_probe_records/3'])])
    assert probe_owners(a)=={0:['first'],3:['other','second']}


def test_missing_owner_or_invalid_pointer_does_not_get_inferred_from_source():
    assert probe_owners(step([test('first',['/component_probe_records/x','/component_probe_records/1/extra'])]))=={}
    assert probe_owners({})=={}
