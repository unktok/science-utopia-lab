from dataclasses import replace

import pytest
import torch

from utopia.optimization.generative_system import (
    GenerativeSystemSpace, op, program_from_expression, seed_generative_system,
    synthesize_program, mutate_program,
)
from utopia.system import DeterministicGraphRunner, MechanismRegistry
from utopia.system.programs import (
    PROGRAM_IMPLEMENTATION, digest, execute_program,
    register_program_interpreter, validate_program,
)


def inputs():
    return {key: torch.tensor([0.2, 0.4, 0.6], dtype=torch.float64)
            for key in ("quality", "novelty", "resources", "knowledge", "signal")}


def test_new_rule_ast_changes_execution_without_registering_a_new_handler():
    linear = program_from_expression({"input": "quality"})
    inverted = program_from_expression(op("sub", {"const": 1}, {"input": "quality"}))
    first, _ = execute_program(linear, inputs(), size=3)
    second, _ = execute_program(inverted, inputs(), size=3)
    assert first[0] < first[2]
    assert second[0] > second[2]
    assert digest(linear) != digest(inverted)


@pytest.mark.parametrize("bad", [
    {"op": "__import__", "args": []},
    {"input": "future_knowledge"},
    {"param": "not_declared"},
    {"const": float("inf")},
    {"op": "add", "args": [{"const": 1}]},
    {"op": "softmax", "args": [{"const": 1}]},
    {"python": "open('/tmp/x', 'w')"},
])
def test_malformed_or_executable_source_never_enters_the_interpreter(bad):
    program = program_from_expression({"input": "quality"})
    program["output"] = bad
    with pytest.raises(ValueError):
        validate_program(program)


def test_resource_limit_prevents_unbounded_ast_execution():
    program = program_from_expression({"input": "quality"})
    expression = {"const": 0.5}
    for _ in range(30):
        expression = op("tanh", expression)
    program["output"] = expression
    with pytest.raises(ValueError, match="resource limit"):
        validate_program(program)


def test_threshold_has_a_hard_interpretation_and_a_genuine_smooth_gradient():
    program = program_from_expression(op("threshold", {"input": "quality"}, {"const": 0.3}))
    world = inputs()
    world["quality"].requires_grad_(True)
    smooth, _ = execute_program(program, world, size=3)
    smooth.sum().backward()
    assert torch.all(world["quality"].grad > 0)
    hard, _ = execute_program(program, inputs(), size=3, hard=True)
    assert hard[0] < hard[1]
    assert hard[1] == hard[2]


def test_state_updates_are_simultaneous_and_recur_across_invocations():
    program = program_from_expression({"state": "memory"})
    program["updates"]["memory"] = op("add", {"state": "memory"}, {"const": 0.5})
    first, state = execute_program(program, inputs(), size=3)
    second, _ = execute_program(program, inputs(), size=3, state=state)
    assert first.tolist() == pytest.approx([torch.tanh(torch.tensor(-0.1)).item()] * 3)
    assert torch.all(second > first)


def test_generated_programs_run_in_existing_graph_runtime_and_resume_exactly():
    system = seed_generative_system()
    space = GenerativeSystemSpace(system)
    candidate, _ = space.mutate_with_record(
        system.to_dict(), seed=19, proposal_index=1, operation="add-node",
    )
    spec = type(system).from_dict(candidate)
    spec = replace(spec, initial_state={
        "population_size": 3,
        "program_inputs": {key: value.tolist() for key, value in inputs().items() if key != "signal"},
    })
    registry = MechanismRegistry()
    register_program_interpreter(registry)
    assert registry.registered == ((PROGRAM_IMPLEMENTATION, 1),)
    runner = DeterministicGraphRunner(spec, registry)
    whole = runner.run(periods=4)
    first = runner.run(periods=2)
    second = runner.run(periods=2, checkpoint=first.checkpoint.to_dict())
    assert [event.to_dict() for event in whole.events] == [
        event.to_dict() for event in (*first.events, *second.events)
    ]
    assert whole.checkpoint.to_dict() == second.checkpoint.to_dict()
    assert any(event.provenance["mechanism_family"] == "custom" for event in whole.events)


def test_synthesis_produces_new_recursive_programs_instead_of_a_finite_system_catalog():
    programs = [synthesize_program(seed=seed) for seed in range(20)]
    for program in programs:
        validate_program(program)
        output, _ = execute_program(program, inputs(), size=3)
        assert torch.isfinite(output).all()
    assert len({digest(program) for program in programs}) >= 15


@pytest.mark.parametrize("operation", [
    "program", "parameter", "add-node", "remove-node", "add-edge", "remove-edge", "delay", "order",
])
def test_rule_structure_and_process_mutations_are_executable(operation):
    system = seed_generative_system()
    candidate, record = GenerativeSystemSpace().mutate_with_record(
        system.to_dict(), seed=113, proposal_index=7, operation=operation,
    )
    GenerativeSystemSpace().validate(candidate)
    assert record["operation"] == operation
    assert record["parent"] != record["child"]
    if operation == "add-node":
        assert len(candidate["mechanisms"]) == len(system.mechanisms) + 1
    if operation == "program":
        assert any(node["parameters"]["program"] != original.parameters["program"]
                   for node, original in zip(candidate["mechanisms"], system.mechanisms))


def test_mutation_uses_declared_symbols_for_a_program_with_custom_names():
    program = {
        "schema": "scienceutopia.mechanism-program.v1",
        "inputs": {"evidence": "vector"}, "parameters": {},
        "state": {"archive": 0}, "output": {"input": "evidence"},
        "updates": {"archive": {"state": "archive"}},
    }
    for seed in range(10):
        changed = mutate_program(program, seed=seed)
        validate_program(changed)
        output, _ = execute_program(changed, {"evidence": torch.tensor([0.2, 0.7])}, size=2)
        assert torch.isfinite(output).all()

