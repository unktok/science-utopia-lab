from pathlib import Path

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system


def loss_spec(metric="native.accepted_decisions", coefficient=-1.):
    return {"schema": "scienceutopia.loss-spec.v1", "id": "native-engineering-count-probe", "version": "1",
            "status": "engineering-only", "optimization_seed_role": "development", "direction": "minimize",
            "per_run": {"intercept": 0., "terms": [{"metric_id": metric, "slice_id": None, "coefficient": coefficient}]},
            "across_seeds": {"aggregation": "mean_plus_population_sd", "dispersion_weight": 0., "minimum_valid_runs": 1}}


def test_system_spec_crosses_native_world_loss_and_observation_boundary(tmp_path, fixed_corpus):
    system = legacy_world_system()
    def factory(spec, run_seed, run_id):
        seed()
        return make_sim(tmp_path / run_id, native=NativeScienceKernel(spec))[0]
    suggestion = Suggestion("native-probe-1", system.to_dict(), 0, "initial")
    result = evaluate_native_suggestion(suggestion, seeds=[42], simulation_factory=factory, loss_spec=loss_spec())
    assert result.status == "complete" and result.loss < 0
    assert result.metadata["world_backend"] == "native-research-world"
    observed = result.metadata["measurements"][0]["metrics"]["native.accepted_decisions"]["value"]
    assert result.loss == -observed
    assert not result.metadata["technical_failures"]


def test_native_technical_failure_is_not_a_loss_penalty():
    def factory(*args):
        raise ValueError("deliberate unavailable native capability")
    system = legacy_world_system()
    result = evaluate_native_suggestion(Suggestion("native-failure", system.to_dict(), 0, "initial"),
        seeds=[42], simulation_factory=factory, loss_spec=loss_spec())
    assert result.status == "failed" and result.loss is None
    assert result.metadata["technical_failures"][0]["loss"] is None
