# Workflow timing: prospective interpretation before completed controls

November14, after first real readiness but before any reference/own world score.
This is an analysis plan, not a change to the frozen3b912d17 experiment,
its losses, proposal budget, selection, failure handling or permissions.

## What is actually manipulated

The literal R7 control allocates liquidity before annual research costs and
the later funding cycle. The hand control moves the same liquidity program,
its effect consumer and costs after funding, changing three phases/five edges.
The code, numeric reserve, original scientist weights and production rules
remain unchanged. This is a joint timing intervention, not an isolated cost-
order or liquidity-order effect. Generated programs may alter other permitted
phases and typed connections; inspect every actual edit against both its
selected parent and the original anchor.

## Native implementation paths that prevent a naive interpretation

- `utopia/system/native_kernel.py`, `NativeScienceKernel._stage` branches:
  the costs phase calls the original `_charge_annual_costs`; funding calls the
  original `_run_phase_5_update_funding`; close seals the resource ledger after
  all mutating effects. No additional funding or fictitious acceptance is
  supplied by the graph syntax.
- `utopia/simulation.py`, `_charge_annual_costs`: only available, active authors
  whose project has not already ended are charged. Consequently equal nominal
  annual cost does not imply equal realized aggregate charges across workflows.
- `_run_phase_5_update_funding` awards resources and then invokes
  `_finish_funding_cycle`. The latter deactivates active author-capable agents
  when their resource value is truthy and at most10. That legacy zero-value
  exception is literal; do not silently replace it with a cleaner threshold.
- In the hand control, attrition therefore occurs before the moved liquidity
  operation and cost phase. Late transfers need not reactivate an already
  removed author. Conversely, a later cost may leave an author at a low balance
  after the year's attrition check. Either effect must be verified in the
  actual events/checkpoints, not inferred solely from a graph's order.
- `_finish_funding_cycle` also records funding-cycle ecosystem summaries.
  Those are stage-time snapshots, not necessarily end-of-year observations
  after the moved liquidity/cost effects. Compare the ledger-close boundary
  and original checkpoint activity state for a common endpoint. Preserve the
  historical stage summaries rather than rewriting them to agree.

These are traceable implementation facts, not a prediction that the hand
control wins or that preserving any group is an extra optimization condition.
There is no fairness, participation, novelty or improvement veto. T and U
remain the declared objectives; resource/activity records explain outcomes.

## Closed-study readout

1. Retain the literal eight-slot upper bound, original nulls and actual model
   costs. Require the two original-source audits and matching independent cost
   and report exports before treating development results as normally closed.
2. Report both cross-scores and both best-own/best-known paths. An improving
   own curve below a poor first proposal is not improvement over a reference.
3. Join each executed phase/effect to its year and owner; report the literal
   changed phases and edge multisets, not only graph hashes or the designer's
   claimed rationale. Schema-valid wiring alone does not prove a changed input.
4. At each year, join opening resources, actual grants, actual transfer debits/
   credits, charged costs and closing balances. Reconcile conservation with
   real external inflows/outflows, including inactive founders; do not impute
   missing checkpoint records as zero. Align activity/attrition changes with
   their actual phase and inspect the subsequent scientific model requests.
5. Interpret accepted records and fixed-content opinions at their declared
   boundary. Neither a surviving author nor a lower T/U is verified real-world
   knowledge gain. Funding-cycle and ledger-close summaries must not be mixed.

## Followup decisions, not a queued expansion

The existing two references do not identify which part of the joint timing
intervention caused a difference. If an important effect is observed, first
inspect its actual mechanism. A potential small factorial followup would hold
sources/parameters fixed and separate early/late liquidity from early/late
costs, with each mixed workflow explicitly validated for typed data freshness
and native effects. It is not enough to rename a phase while retaining a stale
world snapshot. No mixed control or new world is dispatched by this note.

### November14 static decomposition, not an executed followup

The [prospective constructor and actual static exports](../results/native-workflow-timing-corners-static-v1.json)
now verify that all four early/late liquidity-by-cost graphs are legal in the
existing native domain, without changing sources, parameters, effects or initial
state. The original and existing hand control are literal endpoints; mixed
controls do not repair or replace any submitted optimizer policy.

| Liquidity timing | Cost timing | Changed phases | Rewired edges | Liquidity reads | Selection features read |
| --- | --- | --- | --- | --- | --- |
| Early | Early |0|0| Submission snapshot | Costs snapshot |
| Late | Early |2|1| Funding snapshot | Costs snapshot |
| Early | Late |1|4| Submission snapshot | Submission snapshot |
| Late | Late |3|5| Funding snapshot | Submission snapshot |

This clarifies a remaining identification problem, rather than solving it:
moving costs past selection requires a new causal upstream observation route.
With early liquidity but late costs, the submission snapshot can also precede
that year's early transfer. Resource-transfer effects emit receipts, not a new
`world` observation port; one cannot assume that a later consumer receives a
refreshed world merely because its phase moved. The four legal graphs are thus
well-defined **timing-plus-observation policies**, not a pure action-timing
factorial. A future mechanism study must explicitly hold suitable observation
rules constant or separately manipulate them, and retain stale-input failures
if that is the declared policy. Do not silently add a new snapshot capability,
change the fixed pilot or claim an isolated effect from these static graphs.

The eight pure checks and two identical source-bound static exports execute
no native world, model or institutional code. The input anchor is a literal
plan from the stopped workflow attempt; using its graph proves no normal
closure or outcome for that attempt. No new comparison or seed is queued.

Only then fix a finite independent-history/unused-condition comparison and
lock the selected systems before evaluation. Do not choose seeds, refill a
failed proposal, remove a strong control or revise the loss to manufacture a
positive result. If every generated workflow ties or loses, explain the
exercised authority and observed limitations without a global impossibility
claim. A stopped transport instead requires a technical diagnosis, not a
scientific conclusion about institutional design.

## Observed completed-control addendum: November14

The original workflow-v3 study stops at designer readiness, so it has no normal
optimization selection or unused-seed evaluation. A separately scoped read-only
adapter now checks the two completed control cells at their original scientific
source, without fabricating missing original closure or observer-audit files.
Two independent executions give byte-identical reports; this is repeatable
analysis of the same observations, **not independent experimental replication**.
See the [compact proof](../results/native-workflow-v3-stopped-controls-cold-proof-v1.json).

| Observed quantity | R7-original | Hand timing/routing control |
| --- | --- | --- |
| Throughput loss T (minimize) | -18 | -20 |
| Content-utility loss U (minimize) | -13.3333 | -15.3333 |
| Active original authors, end years1–4 | 5,5,4,2 | 5,5,5,5 |
| Original-author resource stock, end years1–4 | 120,90,60,40 | 120,90,60,30 |
| Actual grant income/year | 20,20,20,20 | 20,20,20,20 |
| Actual research fees/year | 50,50,50,40 | 50,50,50,50 |
| Conserving internal transfers/year | 12,13,5,0 | 6,10,17,8 |

The observed difference is not financed by extra aggregate grant income.
Resource distribution and within-year ordering can matter even when aggregate
annual stocks match through year3: the original loses an active author in
year3, whereas the hand policy retains five at that boundary. This is an
operated joint timing/observation-routing comparison with unchanged existing
mechanism implementations, not an isolated causal estimate of fee timing.
In particular, later fee collection and different actual transfers are both
present; end-year stock does not recover intra-year resource minima. The two
losses happen to prefer the same hand control here, so this pair does not
demonstrate objective-dependent institution discovery. Activity and resource
columns explain behavior; they do not add a participation veto to either loss.

The prospective plan above retains its earlier scope and routing caveat.
