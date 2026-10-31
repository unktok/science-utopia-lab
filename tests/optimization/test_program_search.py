from copy import deepcopy
from dataclasses import replace

import pytest
import torch

from utopia.optimization.generative_system import GenerativeSystemSpace, seed_generative_system
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.program_search import (
    gradient_audit, optimize_program_world, search_program_systems,
)
from utopia.system import SystemSpec
from utopia.system.program_world import (
    RelaxedProgramSystem, evaluate_program_system, initial_world, make_world_loss,
    rollout, tensor_loss,
)


def test_gradients_of_entire_world_match_numerical_derivatives_in_six_families():
    audit = gradient_audit(
        RelaxedProgramSystem(seed_generative_system()), [initial_world(811)],
        make_world_loss("production"), periods=2,
    )
    assert audit["all_pass"]
    assert {row["group"] for row in audit["records"]} == {
        "parameters_raw", "rule_logits", "node_logits", "edge_logits",
        "delay_logits", "schedule_logits",
    }
    assert all(abs(row["analytic"]) > 1e-10 for row in audit["records"])


def test_hard_projection_and_common_outer_evaluator_use_same_transition_equations():
    design = RelaxedProgramSystem(seed_generative_system())
    with torch.no_grad():
        design.node_logits["evaluation"].fill_(-3)
        design.rule_logits["research"][1] = 4
        design.delay_logits["e1"].fill_(3)
        design.schedule_logits[-1] = 5
    projected, decisions = design.project()
    assert "evaluation" not in {node.mechanism_id for node in projected.mechanisms}
    assert all("evaluation" not in (edge.source_mechanism, edge.target_mechanism)
               for edge in projected.connections)
    world = initial_world(811)
    loss = make_world_loss("production")
    hard = rollout(design, world, periods=3, hard=True)
    outer = evaluate_program_system(projected, [world], loss, periods=3)
    assert float(tensor_loss(hard["metrics"], loss).detach()) == pytest.approx(outer["loss"], abs=1e-12)
    assert decisions["schedule"] == ["research", "publication", "funding"]


def test_optimizer_follows_rollout_gradients_and_retains_discrete_validation():
    result = optimize_program_world(
        seed_generative_system(), [initial_world(811)], make_world_loss("production"),
        steps=4, periods=2,
    )
    assert result["best_relaxed_loss"] < result["trace"][0]["relaxed_loss"]
    assert result["gradient_audit"]["all_pass"]
    assert result["final_outer"]["status"] == "complete"
    assert result["interpretation"]["qwen_in_autograd"] is False
    assert result["final_outer"]["runs"][0]["history"]


def test_freeing_structure_does_not_silently_mutate_the_parameter_only_experiment():
    system = seed_generative_system()
    design = RelaxedProgramSystem(system, freedom="parameters")
    assert all(name.startswith("parameters_raw.") for name, value in design.named_parameters()
               if value.requires_grad)
    projected, _ = design.project()
    assert projected.connections == system.connections
    assert projected.schedules == system.schedules
    assert len(projected.mechanisms) == len(system.mechanisms)


def test_black_box_loop_invents_programs_and_updates_from_actual_observations():
    system = seed_generative_system()
    report = search_program_systems(system, [initial_world(811)], make_world_loss("production"),
                                    budget=6, periods=2)
    records = report["records"]
    assert len(records) == 6
    assert all(row["observation"]["status"] == "complete" for row in records)
    assert records[2]["suggestion"]["based_on_observation_id"]
    baseline = {node.mechanism_id: node.parameters["program"] for node in system.mechanisms}
    assert any(node["parameters"]["program"] != baseline.get(node["mechanism_id"])
               for row in records for node in row["suggestion"]["candidate"]["mechanisms"])


def test_different_loss_specs_score_the_same_generated_world_differently():
    system = seed_generative_system()
    worlds = [initial_world(811), initial_world(821)]
    production = evaluate_program_system(system, worlds, make_world_loss("production"), periods=2)
    burden = evaluate_program_system(system, worlds, make_world_loss("burden"), periods=2)
    assert production["loss"] < 0 < burden["loss"]
    assert production["loss_spec_sha256"] != burden["loss_spec_sha256"]
    assert production["runs"] == burden["runs"]


def test_tensor_loss_matches_existing_loss_spec_aggregator():
    loss = make_world_loss("knowledge")
    loss["across_seeds"]["dispersion_weight"] = 0.2
    result = evaluate_program_system(seed_generative_system(),
                                     [initial_world(811), initial_world(821)], loss, periods=2)
    standard = evaluate_loss(loss, [{
        "run_id": f"world-{index}",
        "metrics": {key: {"status": "measured", "value": value}
                    for key, value in row["metrics"].items()},
    } for index, row in enumerate(result["runs"])])
    assert standard["loss"] == pytest.approx(result["loss"], abs=1e-12)


@pytest.mark.parametrize("operation", ["order", "delay", "program", "add-node"])
def test_process_or_rule_changes_propagate_to_world_outcomes(operation):
    system = seed_generative_system()
    space = GenerativeSystemSpace(system)
    candidate, _ = space.mutate_with_record(system.to_dict(), seed=19, proposal_index=7,
                                           operation=operation)
    loss = make_world_loss("production")
    worlds = [initial_world(811)]
    baseline = evaluate_program_system(system, worlds, loss, periods=3)
    changed = evaluate_program_system(SystemSpec.from_dict(candidate), worlds, loss, periods=3)
    assert changed["loss"] != pytest.approx(baseline["loss"], abs=1e-10)


def test_numeric_world_rejects_unsupported_program_inputs():
    system = seed_generative_system()
    node = system.mechanisms[0]
    parameters = deepcopy(node.parameters)
    parameters["program"]["inputs"]["future"] = "vector"
    changed = replace(system, mechanisms=(replace(node, parameters=parameters), *system.mechanisms[1:]))
    with pytest.raises(ValueError, match="unavailable"):
        evaluate_program_system(changed, [initial_world(811)], make_world_loss("production"))


def test_empty_institution_graph_is_valid_and_can_acquire_a_new_generated_mechanism():
    empty = SystemSpec("uninstitutionalized-world", 1)
    result = evaluate_program_system(empty, [initial_world(811)], make_world_loss("production"))
    assert result["status"] == "complete"
    assert result["loss"] < 0
    candidate, record = GenerativeSystemSpace(empty).mutate_with_record(
        empty.to_dict(), seed=11, proposal_index=0, operation="add-node",
    )
    assert len(candidate["mechanisms"]) == 1
    assert not candidate["connections"]
    assert record["child"] != record["parent"]


def test_failed_outer_execution_is_recorded_with_no_loss_or_winner(monkeypatch):
    import utopia.optimization.program_search as search

    def fail(*args, **kwargs):
        raise ValueError("technical fixture failure")

    monkeypatch.setattr(search, "evaluate_program_system", fail)
    result = search.search_program_systems(seed_generative_system(), [initial_world(811)],
                                           make_world_loss("production"), budget=1)
    assert result["records"][0]["observation"]["status"] == "failed"
    assert result["records"][0]["observation"]["loss"] is None
    assert result["best_loss"] is None
    assert result["system_spec"] is None

