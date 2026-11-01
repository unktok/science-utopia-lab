"""Opaque native-world evaluation under the existing LossSpec/ask-tell contract."""
from __future__ import annotations

from typing import Callable, Sequence
from pathlib import Path
import math

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.native_kernel import NativeScienceKernel


def measure_native_world(simulation, *, run_id: str):
    """Counts/resources from actual native domain state, not invented quality laws.

    This is a small versioned measurement adapter. It does not select a loss,
    equate publication counts with scientific value, or impose a promotion veto.
    """
    kernel = simulation.native_system
    if kernel is None or kernel.last_year != simulation.num_years:
        raise ValueError("native measurement requires a completed native-world run")
    return _measure_domain(simulation, run_id=run_id, after_year=0)


def measure_native_boundary(simulation, *, run_id: str, after_year: int):
    """Real interval flows and end-boundary stocks, NOT a fresh-world comparison.

    The enclosing session must separately verify the just-saved society boundary.
    Flow counts include only decisions/deliveries after ``after_year``; author
    activity/resources remain current stocks, not differences of stock totals.
    """
    kernel = simulation.native_system
    if (kernel is None or kernel._frame is not None or type(after_year) is not int
            or not 0 <= after_year < kernel.last_year):
        raise ValueError("native interval measurement requires a completed later boundary")
    result = _measure_domain(simulation, run_id=run_id, after_year=after_year)
    result.update(measurement_schema="scienceutopia.native-interval-measurements.v1",
                  interval={"after_year": after_year, "through_year": kernel.last_year},
                  comparison="online-same-society-not-counterfactual")
    return result


def _measure_domain(simulation, *, run_id, after_year):
    kernel = simulation.native_system
    rounds = [r for paper in simulation.paper_tracker.papers_by_id.values()
              for r in paper.review_history if after_year == 0 or r['year'] > after_year]
    authors = [a for a in simulation.ecosystem.agent_population.values() if getattr(a, 'can_author', False)]
    values = {
        "native.accepted_decisions": sum(r.get("decision") == "accept" for r in rounds),
        "native.rejected_decisions": sum(r.get("decision") == "reject" for r in rounds),
        "native.review_records": sum(len(r.get("reviews", [])) for r in rounds),
        "native.final_active_authors": sum(a.is_active for a in authors),
        "native.final_author_resources": sum(a.resources for a in authors),
        "native.institutional_context_deliveries": sum(e.event_type == "native.system.context_delivered"
            and (after_year == 0 or e.year > after_year) for e in kernel.events),
    }
    accepted = [r for r in rounds if r.get('decision') == 'accept']
    values['native.accepted_unreviewed_decisions'] = sum(not r.get('reviews', []) for r in accepted)
    # Use actual reviewer observations, never institution-authored final scores.
    # Empty review sets explicitly contribute zero utility, not a fabricated score.
    peer_score = 0.0
    score_error = None
    for decision in accepted:
        reviews = decision.get('reviews', [])
        scores = [r.get('overall_score') for r in reviews]
        if any(isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s) for s in scores):
            score_error = 'accepted decision has a missing or nonfinite raw reviewer score'
            break
        if scores:
            peer_score += math.fsum(scores) / len(scores)
    metrics = {name: {'status': 'measured', 'value': value} for name, value in values.items()}
    metrics['native.accepted_peer_score_sum'] = (
        {'status': 'unavailable', 'value': None, 'reason': score_error} if score_error else
        {'status': 'measured', 'value': peer_score})
    return {"run_id": run_id, "system_fingerprint": kernel.spec.fingerprint,
            "measurement_schema": "scienceutopia.native-domain-measurements.v1",
            "metrics": metrics}


def evaluate_native_suggestion(suggestion: Suggestion, *, seeds: Sequence[int],
                                simulation_factory: Callable, loss_spec: dict):
    """Execute a complete SystemSpec in the actual Simulation, then measure loss.

    The factory owns isolated paths, model/cache/fidelity and subclass plugins.
    It must return a native Simulation bound to exactly the suggested graph.
    The optimizer receives only observations, not world internals or gradients.
    Durable multi-run scheduling remains the caller's responsibility.
    """
    from utopia.simulation import Simulation
    validate_loss_spec(loss_spec)
    if not seeds or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("native evaluation requires distinct integer seeds")
    spec = SystemSpec.from_dict(suggestion.candidate)
    validate_system_spec(spec).require_valid()
    evaluations, failures, evidence = [], [], []
    for seed in seeds:
        run_id = f"{suggestion.suggestion_id}-s{seed}"
        sim = None
        try:
            sim = simulation_factory(spec, seed, run_id)
            if (not isinstance(sim, Simulation) or not isinstance(sim.native_system, NativeScienceKernel)
                    or sim.native_system.spec.fingerprint != spec.fingerprint):
                raise ValueError("factory did not bind the suggested SystemSpec to the native research world")
            if (getattr(sim.args, "seed", None) != seed
                    or getattr(sim.llm, "run_seed", None) != seed):
                raise ValueError("factory native world/model seed differs from the requested replicate")
            sim.run()
            measurement = measure_native_world(sim, run_id=run_id)
            evaluations.append(measurement)
            evidence.append({"run_id": run_id, "seed": seed, "system_fingerprint": spec.fingerprint,
                             "event_stream_hash": sim.native_system.to_dict()["event_stream_hash"]})
            checkpoint = Path(sim.output_dir) / f'portable_checkpoint_year_{sim.num_years}.json.gz'
            if checkpoint.exists():
                from utopia.utils.data_utils import file_sha256
                evidence[-1].update(checkpoint_path=str(checkpoint.resolve()), checkpoint_sha256=file_sha256(checkpoint))
        except Exception as error:
            failures.append({"run_id": run_id, "seed": seed, "error_type": type(error).__name__,
                             "error": str(error)[:2000], "loss": None})
        finally:
            cache = getattr(getattr(sim, "llm", None), "response_cache", None)
            if cache is not None:
                cache.close()
    loss = evaluate_loss(loss_spec, evaluations)
    complete = loss["status"] == "complete"
    return Observation("observation-" + suggestion.suggestion_id, suggestion.suggestion_id,
        suggestion.candidate, "complete" if complete else "failed", loss["loss"] if complete else None,
        {"world_backend": "native-research-world", "system_fingerprint": spec.fingerprint,
         "loss_spec_sha256": loss_spec_sha256(loss_spec), "loss_evaluation": loss,
         "measurements": evaluations, "technical_failures": failures, "runs": evidence})
