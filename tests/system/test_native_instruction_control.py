"""Developer comparator QA: original phases, not actual-Qwen policy evidence."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, BINDING
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_fixed_production_domain import require_fixed_production
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_information_institution import (
    INSTRUCTION_PROTOCOL, INSTRUCTION_SOURCE, information_system, instruction_control,
)
from utopia.system.native_kernel import NativeScienceKernel

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'
INSTRUCTION = 'STATIC_INSTRUCTION_QA: literal research advice, not a project command. 日本語も保持。'


def anchor():
    return information_system(IMAGE, condition='M0')


def build(**kw):
    options = {'instruction':INSTRUCTION, 'delivery_phase':2}
    options.update(kw)
    return instruction_control(anchor(), IMAGE, **options)


def test_variants_keep_the_literal_producer_and_original_production_laws():
    base = anchor()
    specs = [build(), build(delivery_phase=235), build(connected=False)]
    producers = []
    for spec in specs:
        require_fixed_production(base, spec)
        producer = next(n for n in spec.mechanisms if n.mechanism_id == 'developer-instruction-office')
        producers.append(producer)
        assert producer.parameters['code_artifact']['source'] == INSTRUCTION_SOURCE
        assert producer.parameters['instruction'] == INSTRUCTION
        assert next(s.phase for s in spec.schedules if s.mechanism_id == producer.mechanism_id) == 1
        assert all(n == next(v for v in spec.mechanisms if v.mechanism_id == n.mechanism_id)
                   for n in base.mechanisms)
    assert producers[0] == producers[1] == producers[2]
    assert specs[0].connections == specs[1].connections
    assert not any(e.target_mechanism == 'developer-instruction-receiver' for e in specs[2].connections)


@pytest.mark.parametrize('options', [
    {'instruction':''}, {'instruction':'  '}, {'instruction':None},
    {'instruction':'あ' * 2731}, {'connected':1}, {'first_period':True},
    {'first_period':0}, {'first_period':1.5}, {'delivery_phase':True},
    {'delivery_phase':1}, {'delivery_phase':240}, {'delivery_phase':-2},
])
def test_invalid_explicit_contract_is_rejected_without_execution(options):
    with pytest.raises(ValueError):
        build(**options)


def test_existing_control_is_not_silently_overwritten():
    existing = build()
    with pytest.raises(ValueError, match='fresh instruction'):
        instruction_control(existing, IMAGE, instruction=INSTRUCTION, delivery_phase=2)


def test_protocol_collision_is_not_silently_reused():
    from utopia.system import ArtifactTypeSpec
    base = anchor()
    base = replace(base, artifact_types=(*base.artifact_types, ArtifactTypeSpec(INSTRUCTION_PROTOCOL)))
    with pytest.raises(ValueError, match='fresh instruction'):
        instruction_control(base, IMAGE, instruction=INSTRUCTION, delivery_phase=2)


def test_real_container_native_delivery_timing_and_inert_full_request_equality(
        tmp_path, fixed_corpus, monkeypatch):
    executor = DockerCodeExecutor(IMAGE)
    specs = {'base':anchor(), 'off':build(connected=False),
             'early':build(), 'late':build(delivery_phase=235),
             'second-period':build(first_period=2)}
    snapshots = {}
    for index, (name, spec) in enumerate(specs.items()):
        seed()
        monkeypatch.setattr('time.time', lambda index=index: 1234567890. + index * 86400.)
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        kernel = NativeScienceKernel(spec, code_executor=executor)
        sim, calls = make_sim(tmp_path/name, native=kernel)
        sim.num_years = 2
        try:
            sim.run()
            directions = [(ctx[0][1], INSTRUCTION in json.dumps(payload, ensure_ascii=False))
                for ctx, payload in calls if ctx[0][0] == 'phase1_directions']
            events = [e for e in kernel.events if e.event_type == 'native.system.context_delivered'
                and e.payload['message']['source'] == 'developer-instruction-office']
            plans = [e for e in kernel.events if e.event_type == 'native.system.research_plan_applied']
            assert plans and all(not e.payload['amendments'] for e in plans)
            snapshots[name] = {'calls':deepcopy(calls), 'directions':directions,
                'messages':[deepcopy(e.payload['message']) for e in events],
                'code':[e.payload for e in kernel.events if e.event_type == 'generated.code_executed'
                    and e.mechanism_id == 'developer-instruction-office']}
        finally:
            sim.llm.response_cache.close()
    assert snapshots['base']['calls']
    assert snapshots['base']['calls'] == snapshots['off']['calls']
    assert [p for c, p in snapshots['base']['calls'] if c[0][1] == 1] == [
        p for c, p in snapshots['late']['calls'] if c[0][1] == 1]
    for name, first_year in [('base',None), ('off',None), ('early',1), ('late',2), ('second-period',2)]:
        observed = [year for year, present in snapshots[name]['directions'] if present]
        assert (min(observed) if observed else None) == first_year
    for name, emitted_year in [('early',1), ('late',1), ('second-period',2)]:
        messages = snapshots[name]['messages']
        assert len(messages) == 4
        assert all(m['received_year'] == m['emitted_year'] == emitted_year
            and m['payload'] == {'schema':INSTRUCTION_PROTOCOL, 'instruction':INSTRUCTION} for m in messages)
    assert not snapshots['off']['messages']
    # The same source runs in the same opening slot on/off and early/late.
    # Equal producer results do not imply equal later worlds or prove mediation.
    for name in ('off', 'early', 'late'):
        assert len(snapshots[name]['code']) == 2
    assert [r['result_sha256'] for r in snapshots['off']['code']] == [
        r['result_sha256'] for r in snapshots['early']['code']] == [
        r['result_sha256'] for r in snapshots['late']['code']]
