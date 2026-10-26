# First five-seed paired system comparison

Formal comparison status: **incomplete**.

## Paired objective deltas

All deltas are candidate minus baseline. Intervals are descriptive 95% paired-bootstrap intervals.

| Metric | Mean delta | Median | 95% interval | + / 0 / − |
|---|---:|---:|---:|---:|
| `active_researcher_fraction` | 0.08 | 0.1 | [0.04, 0.1] | 4 / 1 / 0 |
| `low_resource_active_fraction` | 0.16 | 0.2 | [0.08, 0.2] | 4 / 1 / 0 |
| `review_burden` | -0.121838 | -0.136302 | [-0.196982, -0.0466937] | 0 / 1 / 4 |
| `low_resource_review_burden` | -0.207959 | -0.160819 | [-0.348667, -0.0672515] | 0 / 1 / 4 |
| `topic_entropy` | -0.0123958 | 0 | [-0.164942, 0.162412] | 1 / 2 / 2 |

## Seed-level participation

| Seed | Aggregate baseline → candidate | Low-resource baseline → candidate | Eligibility (B/C) |
|---:|---:|---:|---:|
| 101 | 0.8 → 0.9 | 0.6 → 0.8 | feasible / feasible |
| 103 | 0.9 → 1 | 0.8 → 1 | feasible / feasible |
| 107 | 0.7 → 0.8 | 0.4 → 0.6 | infeasible / feasible |
| 109 | 0.8 → 0.9 | 0.6 → 0.8 | feasible / feasible |
| 113 | 0.8 → 0.8 | 0.6 → 0.6 | feasible / feasible |

## Interpretation boundary

The preregistered formal comparison is incomplete because at least one run is infeasible. It is retained rather than discarded or replaced; the five paired deltas are diagnostic evidence.

- The bootstrap interval is descriptive for five simulator seeds.
- No null-hypothesis significance claim is authorized.
- Higher resource input prevents a cost-free dominance claim.
- No real-world causal or optimal-science-policy claim is authorized.
