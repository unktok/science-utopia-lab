# Five-seed paired system comparison

Formal comparison status: **complete**.

## Paired objective deltas

All deltas are candidate minus baseline. Intervals are descriptive 95% paired-bootstrap intervals.

| Metric | Mean delta | Median | 95% interval | + / 0 / − |
|---|---:|---:|---:|---:|
| `active_researcher_fraction` | 0.06 | 0 | [-0.04, 0.18] | 2 / 2 / 1 |
| `low_resource_active_fraction` | 0.12 | 0 | [-0.08, 0.36] | 2 / 2 / 1 |
| `review_burden` | -0.0177564 | -0.075 | [-0.097861, 0.0852619] | 2 / 0 / 3 |
| `low_resource_review_burden` | -0.145657 | -0.175 | [-0.203889, -0.0594737] | 1 / 0 / 4 |
| `topic_entropy` | 0.0113266 | 0 | [-0.0899421, 0.118825] | 2 / 1 / 2 |

## Seed-level participation

| Seed | Aggregate baseline → candidate | Low-resource baseline → candidate | Eligibility (B/C) |
|---:|---:|---:|---:|
| 401 | 0.7 → 1 | 0.4 → 1 | infeasible / feasible |
| 409 | 0.8 → 0.9 | 0.6 → 0.8 | feasible / feasible |
| 419 | 1 → 1 | 1 → 1 | feasible / feasible |
| 421 | 0.8 → 0.8 | 0.6 → 0.6 | feasible / feasible |
| 431 | 0.9 → 0.8 | 0.8 → 0.6 | feasible / feasible |

## Confirmation capability outcome

- Baseline pass/fail/unknown: 4 / 1 / 0
- Candidate pass/fail/unknown: 5 / 0 / 0
- Paired pass→fail / fail→pass: 0 / 1
- Frozen decision: **not_confirmed**
  - candidate harms protected-slice participation in at least one pair

## Interpretation boundary

- The bootstrap interval is descriptive for five simulator seeds.
- No null-hypothesis significance claim is authorized.
- Higher resource input prevents a cost-free dominance claim.
- No real-world causal or optimal-science-policy claim is authorized.
