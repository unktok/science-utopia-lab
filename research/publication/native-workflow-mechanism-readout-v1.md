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

Only then fix a finite independent-history/unused-condition comparison and
lock the selected systems before evaluation. Do not choose seeds, refill a
failed proposal, remove a strong control or revise the loss to manufacture a
positive result. If every generated workflow ties or loses, explain the
exercised authority and observed limitations without a global impossibility
claim. A stopped transport instead requires a technical diagnosis, not a
scientific conclusion about institutional design.
