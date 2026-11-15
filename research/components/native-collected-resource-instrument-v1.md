# Collected activity resources in the original world

This is a passive measurement adapter, not an adopted objective or a simplified
replacement world. Implementation:
`utopia/optimization/native_resource_cost.py`. The existing native evaluator can
use its `measure` function as `measurement_adapter`; every preexisting metric
and identity remains unchanged.

For a complete original trajectory with declared horizon Y:

\[
K=\sum_{y=1}^{Y}\sum_{a\in\text{accounted native authors at }y}
  (c^{research}_{ay}+c^{production}_{ay}+c^{resubmission}_{ay}+c^{application}_{ay}).
\]

The terms are **collected**, reconciled native ledger costs. Include later
entrants and inactive authors if accounted; do not approximate consumption by
the final active count, year-end balances or count times a cost constant.
Exclude grant/industry income and both sides of institutional transfers to
avoid counting reallocations as consumption. Native resource units are not
money, national expenditure, GPU cost, scientific truth or welfare.

`native.collected_activity_resource_cost` is K. A separate diagnostic,
`native.uncollected_activity_resource_cost`, sums requested but uncollected
amounts **in the same four activity categories**, not transfer requests. It is
not added to K or made an eligibility/fairness requirement. A complete known
empty ledger can measure zero; a missing ledger, partial horizon, broken event
chain, unexplained between-year balance or inconsistent source/world contract
cannot. Those are unknown measurements, not numerical penalties.

## Evidence and boundaries

The adapter reads year0 plus every annual portable checkpoint, checks the fixed
world contract/system and cumulative ledger prefix, and invokes the original
`ResourceLedger.reconcile(..., require_closed=True)`. Live and cold entries
bind checkpoint hashes and do not mutate input measurements, raw files, agent
state or RNG. This is local measurement consistency, not a replacement for
physical/source/response auditing.

`scripts/reports/native_resource_cost_v1.py` reconstructs only the already
closed longitudinal **development** study and the known-development-seed choice
controls. It requires distinct byte-matching original audits, exact plan and
raw inventory, clean pinned original sources and a clean external-reader source.
The worker loads the new instrument separately, but explicitly checks that its
checkpoint decoder and ledger reconciler come from the original scientific
checkout. Failed original worlds keep K unknown; no partial cost is an outcome.
Two exports must be compared before retention. This does not rescore unused
evaluation, change original losses/selections or call a model.

The synthetic/software tests cover nonzero fees, clipping, income/transfers,
inactive/later actors, exact live/cold native checkpoints, immutable originals
and unknown versus measured zero. Scripted models/corpus are not real-model
scientific replications.

## Research decision not yet made

One possible *new* study could explicitly minimize `-A + lambda*K`, where A is
the existing accepted-decision count and lambda has units of accepted decisions
per native resource unit. This is implementable by the existing affine
LossSpec evaluator, not a new optimization algorithm. Neither a value of lambda
nor a campaign is adopted here. Any choice informed by historical development
must be labeled as such and tested in a new finite declared study. Do not
change T/U, retune historical selections, require different winners, or count
retrospective reranking as objective-conditioned optimization. Resource-saving
attrition and other undesirable effects must remain visible, not be excluded
by a hidden merit veto. The project still needs a valuable research question,
strong same-authority comparisons and sufficient independent evidence.
