# Native expected-loss gradient estimators v11

## Goal, estimand and boundary

`utopia.optimization.native_expectation_estimators` estimates gradients of a
declared native loss with respect to the **distribution of institutional
designs**. It does not differentiate researcher LLM weights, code strings,
the native simulator or an approximate whole world. Original native Simulation
execution remains the opaque loss oracle. There is no additional merit,
fairness, quality or promotion constraint.

For one fixed generated vocabulary/history, let `A` be the discrete joint
assignment and `Z` independent Gaussian latent coordinates. The institution
receives bounded parameters `lower + (upper-lower)*sigmoid(Z)`. The estimand is

```text
J(theta) = E[A ~ q_logits, Z ~ Normal(mean, fixed_sigma), world randomness]
             [ native_L(System(A, bounded(Z))) ].
theta = (current conditional factor logits, Gaussian latent means).
```

The fixed bounds, generated source, conditional support and coordinate semantics
are held fixed for this derivative. It is NOT a derivative of arbitrary future
vocabulary generation, unknown external author's likelihood, code semantics,
same-society design adoption, or direct author dependence on exposed policy
weights. Distinct latent assignments producing an identical institution remain
distinct draws; no inverse logistic density or candidate deduplication is used.

## Three estimates from the same observations

The module returns plain LR, leave-one-out LR (when `N >= 2`) and optionally a
frozen-prior control-variate estimate. It performs no update or extra native
evaluation. With `s_i = grad_theta log q_theta(A_i,Z_i)`:

```text
plain LR: g = mean_i L_i s_i
LOO LR:   g = mean_i (L_i - mean_{j != i} L_j) s_i
control:  g = mean_i (L_i - c(A_i,Z_i)) s_i
                + grad_theta E_q[c(A,Z)]
```

The control correction is necessary for discrete logits **as well as**
continuous means. Omitting its categorical term gives a biased estimator when
the model depends on categorical choices. The exact existing factor policy
provides complete conditional assignment log probabilities, including forced
choices and parent-dependent supports. Observed choices are never used as a
replacement support and no selected subset is re-normalized.

For a constant native loss, raw LR can have nonzero finite-sample noise; LOO
gives exactly zero advantages. A prior-fitted control can also leave finite
noise. Equal losses are recorded rather than rerolled or forced to yield an
improvement. Zero costs with no control produce a zero gradient. A singleton
batch supports plain/control LR but has no LOO or standard-error comparator.

## Frozen prior-only model and exact correction

`FrozenDesignControlVariate` is a frozen dataclass with tuple coefficients and
explicit training sample/batch IDs. A positive-ridge least-squares fit uses only
completed **previous batches**:

```text
c(a,z) = b + sum_j u_j z_j + sum_j v_j z_j^2 + w[a]
E_q[c] = b + sum_j u_j mean_j
             + sum_j v_j (mean_j^2 + sigma_j^2)
             + sum_a q_logits(a) w[a].
```

`w` is an indicator coefficient for each complete joint assignment, not an
independence approximation for marginal categories. Existing upstream support
enumeration caps apply. Correction gradients are computed through this exact
finite expectation and Gaussian moments; no learned approximation of this
expectation is substituted. Interactions omitted by this additive model remain
inside the native-loss residual, so model misspecification by itself does not
bias the corrected expectation under the stated assumptions.

Current sample IDs must be disjoint from training sample IDs; the current batch
ID cannot occur among training batches. The estimator rejects any overlap.
IDs alone cannot prove chronology or independence: the durable campaign must
audit that fitting occurs before current sampling, never fit on current costs,
and freeze the full record. Same dimensions alone do not establish semantic
compatibility: source, factors, paths, bounds and other relevant semantics must
also match. Changed source/wiring or coordinate meanings require a compatible
new model or an explicit plain-LR fallback, not silent cross-vocabulary reuse.

Two prior observations are enough to define a ridge fit but do not identify a
reliable quadratic response model. The control can **increase** variance.
Within-batch estimated standard errors are diagnostics, not proof of variance
reduction or confidence in an institutional improvement. Numerical exactness of
the correction does not imply accuracy of the fitted native response model.

## Assumptions and fail-closed behavior

Unbiasedness is conditional on fixed current vocabulary/history, IID current
draws, correct normalized likelihood/score on fixed support, a genuinely
prior-only frozen control, finite integrable terms permitting exchange of
derivative and expectation, and no additional direct loss dependence on policy
parameters. Native world stochasticity is allowed provided its conditional
generation law introduces no omitted direct parameter dependence. Fixed
researcher LLM weights do not imply frozen responses.

All draws are retained. Any null/nonfinite loss, technical draw failure, invalid
support or detached likelihood, overlapping control training, nonfinite fit,
score, correction, estimate or diagnostic produces `status: invalid` and
`gradient: null`. No numerical penalty, replacement sample, failed-subset
estimate or parameter mutation is performed. `torch.autograd.grad` does not
populate the caller's `.grad` buffers. Inputs are float64 CPU tensors; sigma is
fixed, not an optimized parameter in this implementation.

## Public API and receipts

```python
control = FrozenDesignControlVariate.fit(
    prior_draws, prior_losses, sample_ids=prior_sample_ids,
    batch_ids=prior_batch_ids, assignments=mixed.policy.assignments,
    latent_dim=len(mixed.coordinates),
)
receipt = estimate_expected_loss_gradient(
    draws, native_losses,
    logits=mixed.policy.logits, mean=mixed.mean, sigma=mixed.sigma,
    discrete_log_probability=mixed.policy.action_log_probability,
    assignments=mixed.policy.assignments, control_variate=control,
    sample_ids=observation_ids, batch_id=request_sha256,
)
```

For no discrete factors, pass `logits={}` and omit the callback/support; for no
continuous dimensions, pass empty float64 vectors. Fit records serialize with
strict `to_dict`/`from_dict`. Reports preserve per-draw scores, per-draw corrected
gradient terms, exact correction, model predictions, all three gradient
comparators, sample/batch IDs, stated estimand and assumptions, and null-on-error
reasons. Fit/reload and receipt replay are deterministic on the tested CPU
environment; cross-library/platform bitwise identity is not asserted.

## Verification and research connection

`tests/optimization/test_native_expectation_estimators.py` checks complete
conditional discrete enumeration; Gaussian quadrature against analytic mixed
quadratic expectations including an interaction absent from the control model;
nonzero exact categorical correction; prior-only exclusion; zero/equal costs;
singleton/identity cases; detached likelihoods; invalid/failure/overflow guards;
and byte-identical frozen-model reload. These are software mathematical QA,
not empirical claims about native institution quality or gradient variance.

The distinction between likelihood-ratio and reparameterization methods follows
[Parmas and Sugiyama, AISTATS 2021](https://proceedings.mlr.press/v130/parmas21a.html).
[Parmas, Seno and Aoki, ICML 2023](https://proceedings.mlr.press/v202/parmas23a.html)
studies composite LR/RP estimators in model-based RL. The present implementation
is a corrected frozen control-variate LR estimator, **not TPX**, not an
inverse-variance blend, and not an ordinary pathwise gradient of the native
research world. A future learned-model gradient cannot simply be averaged with
native LR while assuming its model bias disappears.
