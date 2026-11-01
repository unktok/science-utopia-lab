# Native conserving-resource capability v5

This adds a real native effect beyond publication decisions, context messages
and artifact storage. It is a small **transfer capability**, not a funding
policy, a general funding ontology or useful institutional-invention result.
No new live-Qwen world was run; all validation uses scripted replies/corpus
while executing the original researcher phases and real isolated Python code.

## Open institution -> actual native balances

Any explicitly connected institution can choose transfers through arbitrary
Python/LLM logic and its own declared output protocol. The host does not choose
recipients, priorities, thresholds, allocation amounts, fairness criteria or an
objective. A native consumer, `native.world.resource-transfers.v1`, interprets
each incoming envelope's payload as exactly:

```json
{"transaction_id":"chosen-by-institution","from_actor":"actual-author-id","to_actor":"actual-author-id","amount":7.0}
```

`add_resource_transfer_receiver(spec, source=..., source_port=..., phase=...,
latency=...)` explicitly grants that connected producer port the capability.
The bridge changes the real existing author objects using their native
`update_resources` method. It does not construct a miniature resource world.
Subsequent actual research/funding prompts therefore observe altered balances.
Normal activation/deactivation semantics remain native: receiving a transfer
does not automatically reactivate an inactive researcher.

## Technical domain contract, not a merit veto

- Both actors must already exist and be author-capable. No actor creation,
  treasury, minting, debt, external grant supply or research-plan command is
  implemented by this capability.
- Transfers are between **distinct** actors and amounts are finite, strictly
  positive and available at that point in the declared
  input order. Whole batches are preflighted against staged balances before
  any native mutation; later commands may spend earlier incoming transfers.
  Zero/self commands are rejected before any update call, not implemented as
  debit/credit no-ops that could accidentally trigger native actor side effects.
- Debited and credited amounts must each be **exactly representable** in the
  existing numeric actor balances: actual debit == requested amount == actual
  credit. This prevents a large floating-point balance swallowing a debit while
  the recipient receives funds. `0.25` can be exactly realizable; `0.1` at some
  balances is not and is rejected, not silently rounded or minted. This is a
  finite-precision domain limitation, not an allocation-policy preference.
- Native ledger attachment/open-year/duplicate-leg checks happen before
  application. Unexpected execution failures roll back all touched balances,
  active flags and the entire same ledger object's state. Atomicity covers this
  transaction batch, not the whole scientific year: a later phase failure still
  requires restoring the preceding portable checkpoint. Rollback covers native
  resources/is_active and ledger state, not arbitrary additional side effects
  introduced by a custom host-side override of an actor's update method.
- A transfer identity is the exact producer mechanism, producer port, emitted
  period and chosen transaction ID. Exact repeated delivery is a global no-op
  across consumers and past years; reusing an identity for a different command
  fails closed. A new year can legitimately reuse the institution's local ID.

The transfer rule conserves already modeled resources. It adds no hidden
participation, quality, fairness or promotion constraint. Other world semantics
such as minting would require a separately explicit capability, not a silent
reinterpretation of these transfer commands.

## Accounting, source lineage and continuation

The ledger's original six default categories and default serialization are
unchanged. Only a real transfer opts that ledger instance into the separate
`institution_transfer_in/out` categories and a checkpointed capability flag.
The old four serialization keys remain exact when the capability is absent.
No income/cost category is falsely reused to disguise a transfer as a grant.

Each `native.system.resource_transferred` event records the command hash,
source/port/emitted period/ID identity, actual debit/credit, before/after
balances, receiving period and causal source event IDs. Runtime provenance also
binds the source SystemSpec and consumer implementation. For generated Python,
the causal event is the actual `generated.code_executed` receipt, which in turn
binds exact code, context, result and pinned image. Ledger legs use the same
transaction key as their reason; native consumer memory retains the receipts.

Existing delayed graph delivery, portable checkpoints and cold restart carry
these states without reapplying already committed transfers. The capability
does not mutate the system graph, rewrite old events, add a model request or
change RNG. The additional execution code changes the runtime tree: future live
experiments require a fresh clean source pin, never reuse of old execution
identity. Existing pinned live experiments were not edited.

## Software evidence and limits

An independent review caught the aggregate-float-sum loophole; per-leg exact
representability and adversarial regressions now cover it. The first QA run
also retained one Docker daemon wall/cleanup timeout during year6 of the
**disconnected** producer; production Docker/CPU/memory/time limits were not
weakened. A serial rerun of the native/accounting/migration group passed
**63 tests, 1 skipped in71.54seconds**. After the precision fix and stronger
clock-matched prompt comparison, the focused suite passed **15 tests in20.92s**.

The suite verifies six-year original/native equality when the bridge is absent;
real generated-code commands reaching six years of native balances and
classified ledger legs; matching causal code events; changed funding-level
prompts under fixed clocks/seed contexts; whole-batch rejection, rollback,
cross-year duplicate prevention, fractional representability; and a six-year
delayed-delivery run interrupted and cold-restarted without duplicate effects.
These are software integration proofs with scripted model replies, not evidence
of live-model adaptation, optimization benefit or scientific value.

The wider gaps remain: native research/submission/funding phases still have
private frame prerequisites; new agent-type declarations do not instantiate new
actor behavior; arbitrary Python and native LLM responses do not acquire
autograd through this capability. Those are distinct future implementation
tasks, not claims made by this transfer bridge.
