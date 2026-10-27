"""Pre-registered analyses for metric-conditioned held-out comparisons."""
from __future__ import annotations

import math
import statistics
from typing import Any, Mapping


def _average_ranks(values: Mapping[str, float], *, minimize: bool) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: item[1], reverse=not minimize)
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = ((index + 1) + end) / 2
        for name, _ in ordered[index:end]:
            ranks[name] = rank
        index = end
    return ranks


def _kendall_tau_b(left: Mapping[str, float], right: Mapping[str, float]) -> float | None:
    names = sorted(set(left) & set(right))
    concordant = discordant = left_ties = right_ties = 0
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            a = left[first] - left[second]
            b = right[first] - right[second]
            if a == 0 and b == 0:
                continue
            if a == 0:
                left_ties += 1
            elif b == 0:
                right_ties += 1
            elif a * b > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + left_ties)
        * (concordant + discordant + right_ties)
    )
    return (concordant - discordant) / denominator if denominator else None


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    lm, rm = statistics.fmean(left), statistics.fmean(right)
    numerator = math.fsum((a - lm) * (b - rm) for a, b in zip(left, right))
    denominator = math.sqrt(
        math.fsum((a - lm) ** 2 for a in left)
        * math.fsum((b - rm) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None


def _profile_key(profile: Mapping[str, Any]) -> str:
    return profile["id"] + (f"/{profile['slice']}" if profile.get("slice") else "")


def _scalar_seed_columns(
    profiles: Mapping[str, list[Mapping[str, Any]]],
) -> tuple[dict[str, dict[str, dict[int, float]]], dict[str, str]]:
    columns: dict[str, dict[str, dict[int, float]]] = {}
    directions: dict[str, str] = {}
    for system, items in profiles.items():
        for profile in items:
            key = _profile_key(profile)
            numeric = {
                int(item["seed"]): float(item["value"])
                for item in profile["seed_values"]
                if isinstance(item.get("value"), (int, float))
                and not isinstance(item.get("value"), bool)
                and math.isfinite(float(item["value"]))
            }
            if numeric:
                columns.setdefault(key, {})[system] = numeric
                directions[key] = profile["direction"]
    return columns, directions


def _loss_seed_columns(
    losses: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, dict[str, dict[int, float]]]:
    columns: dict[str, dict[str, dict[int, float]]] = {}
    for system, system_losses in losses.items():
        for loss_id, result in system_losses.items():
            values = {
                int(item["seed"]): float(item["loss"])
                for item in result.get("held_out_seed_values", [])
                if isinstance(item.get("loss"), (int, float))
            }
            if values:
                columns.setdefault(f"loss:{loss_id}", {})[system] = values
    return columns


def _mean_by_system(column: Mapping[str, Mapping[int, float]]) -> dict[str, float]:
    return {
        system: statistics.fmean(values.values())
        for system, values in column.items()
        if values
    }


def rank_reversal_analysis(
    profiles: Mapping[str, list[Mapping[str, Any]]],
    losses: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    metric_columns, directions = _scalar_seed_columns(profiles)
    loss_columns = _loss_seed_columns(losses)
    columns = {**metric_columns, **loss_columns}
    rankings: dict[str, Any] = {}
    for key, values in columns.items():
        means = _mean_by_system(values)
        direction = "minimize" if key.startswith("loss:") else directions[key]
        minimize = direction == "minimize"
        ranks = _average_ranks(means, minimize=minimize)
        rankings[key] = {
            "direction": direction,
            "preference_interpretation": direction in {"minimize", "maximize"},
            "means": means,
            "ranks": ranks,
            "raw_order": sorted(ranks, key=lambda system: (ranks[system], system)),
        }
    taus = []
    reversals = []
    keys = sorted(rankings)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            tau = _kendall_tau_b(rankings[left]["ranks"], rankings[right]["ranks"])
            taus.append({"left": left, "right": right, "kendall_tau_b": tau})
            left_top = rankings[left]["raw_order"][0]
            right_top = rankings[right]["raw_order"][0]
            if left_top != right_top:
                reversals.append({
                    "left": left,
                    "right": right,
                    "left_top_system": left_top,
                    "right_top_system": right_top,
                })
    own_loss = {}
    for system, system_losses in losses.items():
        own_id = next(iter(system_losses), None)
        # Campaign id and LossSpec id need not be lexically equal; the caller
        # marks the own loss explicitly in each result.
        for loss_id, result in system_losses.items():
            if result.get("is_own_loss"):
                own_id = loss_id
                break
        own_loss[system] = {
            "loss_id": own_id,
            "held_out_best_system": (
                rankings.get(f"loss:{own_id}", {}).get("raw_order", [None])[0]
                if own_id else None
            ),
        }
        own_loss[system]["own_winner_remains_best"] = (
            own_loss[system]["held_out_best_system"] == system
        )
    return {
        "columns": rankings,
        "pairwise_kendall_tau_b": taus,
        "winner_reversals": reversals,
        "own_loss_check": own_loss,
    }


def paired_tradeoff_analysis(
    profiles: Mapping[str, list[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    columns, directions = _scalar_seed_columns(profiles)
    results: list[dict[str, Any]] = []
    for metric, systems in sorted(columns.items()):
        names = sorted(systems)
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                seeds = sorted(set(systems[left]) & set(systems[right]))
                deltas = [systems[left][seed] - systems[right][seed] for seed in seeds]
                n = len(deltas)
                mean = statistics.fmean(deltas) if deltas else None
                sd = statistics.stdev(deltas) if n >= 2 else None
                se = sd / math.sqrt(n) if sd is not None else None
                # The preregistered split has n=5 (df=4).
                t_critical = 2.7764451051977987 if n == 5 else None
                results.append({
                    "metric": metric,
                    "direction": directions[metric],
                    "left": left,
                    "right": right,
                    "paired_seeds": seeds,
                    "raw_deltas_left_minus_right": deltas,
                    "mean_delta": mean,
                    "paired_sd": sd,
                    "ci95": (
                        [mean - t_critical * se, mean + t_critical * se]
                        if mean is not None and se is not None and t_critical is not None
                        else None
                    ),
                    "paired_effect_dz": mean / sd if sd not in {None, 0.0} else None,
                })
    return results


def _profile_means(profiles: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for system, items in profiles.items():
        result[system] = {}
        for profile in items:
            key = _profile_key(profile)
            result[system][key] = profile.get("summary", {}).get("mean")
            if profile["id"] == "funding-and-resource-ledger":
                structured = profile.get("structured_summary", {})
                result[system]["ending-resource-gini"] = (
                    structured.get("ending_resources.gini", {}).get("mean")
                )
    return result


def gaming_flags(profiles: Mapping[str, list[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    means = _profile_means(profiles)
    flags: list[dict[str, Any]] = []
    for system, current in means.items():
        for comparator, other in means.items():
            if system == comparator:
                continue
            signatures = {
                "burden_without_coverage_or_activity": (
                    current.get("review-burden-per-active-researcher") is not None
                    and other.get("review-burden-per-active-researcher") is not None
                    and current["review-burden-per-active-researcher"]
                    < other["review-burden-per-active-researcher"]
                    and any(
                        current.get(key) is not None and other.get(key) is not None
                        and current[key] < other[key]
                        for key in ("review-coverage", "submission-count", "accepted-paper-count")
                    )
                ),
                "entropy_without_participation_or_activity": (
                    current.get("topic-entropy") is not None
                    and other.get("topic-entropy") is not None
                    and current["topic-entropy"] > other["topic-entropy"]
                    and any(
                        current.get(key) is not None and other.get(key) is not None
                        and current[key] < other[key]
                        for key in (
                            "active-researcher-fraction",
                            "active-researcher-fraction/low-resource-researchers",
                            "submission-count",
                        )
                    )
                ),
                "aggregate_participation_distributional_tradeoff": (
                    current.get("active-researcher-fraction") is not None
                    and other.get("active-researcher-fraction") is not None
                    and current["active-researcher-fraction"]
                    > other["active-researcher-fraction"]
                    and (
                        (
                            current.get("active-researcher-fraction/low-resource-researchers")
                            is not None
                            and other.get("active-researcher-fraction/low-resource-researchers")
                            is not None
                            and current["active-researcher-fraction/low-resource-researchers"]
                            < other["active-researcher-fraction/low-resource-researchers"]
                        )
                        or (
                            current.get("ending-resource-gini") is not None
                            and other.get("ending-resource-gini") is not None
                            and current["ending-resource-gini"] > other["ending-resource-gini"]
                        )
                    )
                ),
            }
            for signature, triggered in signatures.items():
                flags.append({
                    "system": system,
                    "comparator": comparator,
                    "signature": signature,
                    "triggered": triggered,
                    "interpretation": "diagnostic flag only; not technical invalidity or rejection",
                })
    return flags


def generalization_gaps(
    freeze: Mapping[str, Any],
    losses: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    result = {}
    for winner in freeze["winners"]:
        system = winner["campaign_id"]
        loss_id = winner["loss_spec"]["id"]
        held_out = losses[system][loss_id]
        development = float(winner["optimization_observation"]["loss"])
        held_value = held_out.get("loss")
        result[system] = {
            "loss_id": loss_id,
            "optimization_split_incumbent_loss": development,
            "held_out_aggregate_loss": held_value,
            "held_out_seed_values": held_out.get("held_out_seed_values", []),
            "generalization_gap_held_out_minus_optimization": (
                float(held_value) - development if isinstance(held_value, (int, float)) else None
            ),
            "retrospective_all_candidate_rerank": {
                "status": "not_identified",
                "reason": "the preregistered held-out budget evaluates only the three frozen winners, not all five candidates per arm",
            },
        }
    return result


def resolution_analysis(
    profiles: Mapping[str, list[Mapping[str, Any]]],
    losses: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    columns, directions = _scalar_seed_columns(profiles)
    loss_columns = _loss_seed_columns(losses)
    columns.update(loss_columns)
    directions.update({key: "minimize" for key in loss_columns})
    result = {}
    for metric, systems in columns.items():
        if len(systems) < 2:
            continue
        means = _mean_by_system(systems)
        mean_values = list(means.values())
        exact_pairs = total_pairs = 0
        paired_ses: list[float] = []
        paired_contrast_sds: dict[str, float | None] = {}
        contrast_means: list[float] = []
        names = sorted(systems)
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                total_pairs += 1
                if abs(means[left] - means[right]) <= 1e-12:
                    exact_pairs += 1
                seeds = sorted(set(systems[left]) & set(systems[right]))
                deltas = [systems[left][seed] - systems[right][seed] for seed in seeds]
                contrast_means.append(abs(statistics.fmean(deltas)))
                if len(deltas) >= 2:
                    contrast_sd = statistics.stdev(deltas)
                    paired_ses.append(contrast_sd / math.sqrt(len(deltas)))
                    paired_contrast_sds[f"{left}__minus__{right}"] = contrast_sd
                else:
                    paired_contrast_sds[f"{left}__minus__{right}"] = None
        floor = max(
            1e-12,
            2.7764451051977987 * statistics.median(paired_ses) if paired_ses else 1e-12,
        )
        within_by_name = {
            name: statistics.pstdev(values.values())
            for name, values in systems.items() if values
        }
        within_sds = list(within_by_name.values())
        pooled = math.sqrt(statistics.fmean(sd * sd for sd in within_sds)) if within_sds else 0
        system_sd = statistics.pstdev(mean_values) if len(mean_values) > 1 else 0
        full_ranks = _average_ranks(means, minimize=directions[metric] == "minimize")
        common_seeds = sorted(set.intersection(*(set(values) for values in systems.values())))
        loo_spearman = []
        top_stable = []
        for omitted in common_seeds:
            loo_means = {
                name: statistics.fmean(value for seed, value in values.items() if seed != omitted)
                for name, values in systems.items()
                if len(values) > 1
            }
            loo_ranks = _average_ranks(
                loo_means, minimize=directions[metric] == "minimize"
            )
            common = sorted(set(full_ranks) & set(loo_ranks))
            rho = _pearson(
                [full_ranks[name] for name in common],
                [loo_ranks[name] for name in common],
            )
            if rho is not None:
                loo_spearman.append(rho)
            top_stable.append(
                min(full_ranks, key=lambda name: (full_ranks[name], name))
                == min(loo_ranks, key=lambda name: (loo_ranks[name], name))
            )
        inside = sum(value <= floor for value in contrast_means)
        median_rho = statistics.median(loo_spearman) if loo_spearman else None
        low_resolution = (
            inside > len(contrast_means) / 2
            or median_rho is None
            or median_rho < 0.8
        )
        result[metric] = {
            "direction": directions[metric],
            "exact_aggregate_tie_rate": exact_pairs / total_pairs if total_pairs else None,
            "within_system_population_sd": within_by_name,
            "paired_contrast_sd": paired_contrast_sds,
            "system_to_seed_signal_ratio": system_sd / pooled if pooled else None,
            "leave_one_seed_out_spearman": loo_spearman,
            "median_leave_one_seed_out_spearman": median_rho,
            "top_rank_stability_fraction": (
                sum(top_stable) / len(top_stable) if top_stable else None
            ),
            "empirical_resolution_floor": floor,
            "pairwise_contrasts_inside_floor": inside,
            "pairwise_contrast_count": len(contrast_means),
            "low_resolution": low_resolution,
        }
    return result


def build_analyses(
    *,
    freeze: Mapping[str, Any],
    profiles: Mapping[str, list[Mapping[str, Any]]],
    losses: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    generalization = generalization_gaps(freeze, losses)
    flags = gaming_flags(profiles)
    for system, result in generalization.items():
        gap = result["generalization_gap_held_out_minus_optimization"]
        flags.append({
            "system": system,
            "comparator": "same-system-development-split",
            "signature": "development_improvement_without_held_out_transfer",
            "triggered": isinstance(gap, (int, float)) and gap > 0,
            "evidence": {"held_out_minus_optimization_loss": gap},
            "interpretation": "generalization diagnostic only; not technical invalidity or rejection",
        })
    return {
        "rank_reversal": rank_reversal_analysis(profiles, losses),
        "paired_tradeoffs": paired_tradeoff_analysis(profiles),
        "gaming_flags": flags,
        "generalization": generalization,
        "secondary_resolution": resolution_analysis(profiles, losses),
    }
