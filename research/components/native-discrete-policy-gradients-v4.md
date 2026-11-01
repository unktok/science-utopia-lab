# Native discrete policy gradients and audit recovery v4

This is a new optimization route over the **original Simulation**, not a new
numeric world. `NativeDiscretePolicySearch` learns categorical probabilities over
arbitrary complete SystemSpecs, or a Bernoulli probability over two complete
designs. Candidate source, protocols and wiring need not come from a host menu;
however the optimizer receives a finite explicit set and **does not invent it**.

For sampled action `a` and actual full-native loss `L`, autograd computes
`(L - fixed_baseline) * grad(log p_theta(a))`. Its expectation is the gradient
of expected native-world loss, provided draws are valid and the native runtime
depends on theta only through the selected design. This is exact policy-score
calculus with a Monte Carlo estimate; it is **not pathwise backpropagation**
through Python, retrieval, text, tokens or the whole native world. Researcher LLM
weights stay fixed, while all subsequent calls run and can respond to design.

The baseline is fixed independently of all draws, not batch-mean subtraction.
Sample RNG seeds, actions, exact log probabilities, candidates and pending batch
are recorded and deterministically replayed. Duplicate actions remain separate
world executions; dropping them would change the sampling measure. Failed runs
produce no numerical penalty and suppress the whole batch update rather than
conditioning on success. A zero/noisy estimate is not rerolled.

The existing durable campaign accepts this policy as well as the older
Gaussian-logistic score estimator. Successful discrete observations must reopen
their exact checkpoint hash and match source, fixed model, corpus, design and
replicate seed before any update and on resume. LossSpec is unchanged; no
fairness, merit, novelty or participation veto is introduced.

## Verification and boundaries

- Analytic enumeration of categorical and Bernoulli outcomes verifies expected
  log-probability gradients against exact expected-cost autograd and closed form.
- Sample-wise autograd, fixed-baseline invariance in expectation, pending RNG/
  action/log-probability tampering, native checkpoint binding and invalid-batch
  behavior are tested.
- A real native lifecycle QA test uses scripted model transport and corpus,
  isolated generated Python selection, actual domain costs, interruption and
  resume. It is **not a new live-Qwen experiment**.
- CLI: `scripts/run_native_discrete_policy.py`; requires a shared inference lock,
  explicit designs/loss/cache and bounded samples/batches. Live use requires a
  separately approved, clean pinned experiment plan. No live campaign is claimed
  by this implementation note.

## Existing v3 evidence recovery

The completed six calibration worlds and one proposal were preserved despite
the final auditor failing on a relative SQLite URI. Auditors now normalize
programmatic path inputs before making read-only absolute SQLite URIs; absolute
and relative forms have regression tests. Recovery script
`scripts/recover_native_transition_v3_audit.py` only reads existing outputs,
independently re-extracts/refits/replays/verifies and writes a **new** receipt
outside both archives. A manifest verifies every archived file unchanged.
Original failed receipts remain intact. No inference or native world is rerun.

The interpretation is unchanged by fixing bookkeeping: represented backward is
implemented, but native secant fidelity failed; the fresh proposal's loss -3
ties the training best -3. Neither exact native pathwise differentiation,
optimization gain beyond the observed training best nor scientific improvement
is established.
