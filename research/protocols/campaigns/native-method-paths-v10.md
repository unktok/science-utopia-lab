# V10: institution update paths, represented gradients versus black-box search

Fixed before NEW native/Qwen inference. This is a small development comparison,
not population/seed/horizon scale-up, held-out accuracy, optimizer superiority or
useful-invention certification. Keep the original five authors/two native years,
seed42, four-year real-paper corpus, fixed Qwen3:8B and existing charter graph.
Only the review-charter evidence weight varies in[0.2,0.8]. Model weights,
native integer parser, selection thresholds and scientific world laws stay fixed.

## Fixed loss and common information

Use EXACT existing LossSpec `native-joint-v5-net-reviewed-utility`,
`L = 3.25 A - Q + 0.05 R`. No quality/fairness/participation/promotion constraint.
Technical failure has null loss, never a numerical penalty. Both methods receive
only the SAME three historical calibration observations at0.2/0.5/0.8 from
the committed v9-a3 audit, content SHA
`92d6a9b630d9bcd44e379ec48833aed2de71490b85907068fed740361826abbf`.
Their native losses are0.9/0.9/0.8166667. Each arm is charged three historical
evaluations; the underlying physical data/calls are counted once, not twice.
Equal evaluation budget is not identical oracle capability: the represented
method uses saved individual review responses/native traces, whereas the black-
box policy uses only coordinates and measured scalar losses. Both start from
the same full endpoint data; this methodological distinction is reported, not
interpreted as a controlled comparison of equal-information oracle methods.
All v9 data are now development knowledge, NOT new held-out evidence. V9's
unused outcomes are not fed to either optimizer. Posthoc v9 diagnostics motivated
this prospectively new method comparison; they do not revise the frozen v9 result.

Both methods start their CURRENT coordinate at0.5; both already have historical
INCUMBENT0.8. Plot current/proposed values separately from the best observed
system. Incumbent means minimum observed fixed loss, with earliest-observation
ties. No unseen outcome or cross-arm feedback may enter a proposal.

## Frozen methods and online updates

Gradient method: at steps0/1/2 use temperatures[1.0,0.2,0.05] respectively.
At each step refit the original affine raw-response representation using the
three shared historical endpoints and ONLY its OWN earlier completed endpoints.
Temperature is the singleton scheduled value, not chosen by outcome RMSE or
unused performance. Compute the represented gradient at the current coordinate;
update `theta_next = clip(theta + clip(-0.5*g, -0.10, 0.10), 0.2, 0.8)`.
Keep the raw gradient: no sign normalization, forced movement, perturbation
fallback or favorable endpoint substitution. A no-op still consumes its declared
fresh native evaluation. Worsening steps update current; incumbent is separate.
The coarse-to-sharp surrogate does NOT change the actual native objective.

Black-box method: use no derivative or response representation. Sort all distinct
observed coordinates, take intervals immediately adjacent to its observed
incumbent, and bisect the widest interval (lower interval breaks equal-width
ties). Add ONLY its own next native observation and repeat. This deterministic
one-dimensional local interval refinement is a baseline, not an optimal global
black-box algorithm. Record all ties/worse observations without promotion veto.

Historical/fresh endpoint source identities stay intact. The explicit v10 fitter
accepts cross-source data ONLY after every original `utopia/` blob at each source
matches current bytes, real endpoint/loss/raw correspondence checks pass, and
exact pre-intervention controls agree. The only world metadata differences are
source commit, campaign classification and experiment.protocol. All other world,
model, corpus, seed, initial science state, noncoordinate design and objective
bindings must match. No v9 source rewriting or weakened default v9 fitter.

## Budget, ordering and provenance

Six NEW native attempts maximum, three per arm, ordered exactly
G0,B0,G1,B1,G2,B2. This is equal native-evaluation budget, not necessarily equal
physical response counts. Source and plan are frozen in a clean experiment
worktree. Each proposal/operator/eligible-history hash is persisted before its
world starts. Record declared content order, not authenticated wall-clock proof.
Any technical failure stops this campaign and remains null; no replacement or
silent reroll. A separate prospective amendment is required before new attempts.

Use the SAME actual a1 pre-intervention anchor and v9 coupling: only byte-exact
historical requests replay the53 original actual replies, original native
Year1 review insertion executes before coupling identity-checked operational
review_time metadata, and Year2 reviews/later replies are FRESH Qwen calls.
The entire original forward executes. Preserve per-world SQL/wire/checkpoint/
code/task/completion/clock receipts. New calls, logical responses, historical
replays and shared original calls are separate ledgers. Six trajectories are
conditional on ONE shared observed society, not independent replications.

## Completion and interpretation

Independently reconstruct policies, exact eligible histories, scheduled fits,
backwards, projections, every original native loss and reply accounting. Keep
all raw files immutable. Plot proposal/current paths, actual losses, incumbent
paths and costs. Report improvement relative to BOTH the initial center and the
best historical point. Re-evaluating a known best is not new discovery; same-theta
loss differences can reflect Qwen stochasticity, not institutional redesign.
No statistical superiority, causal policy value, useful invention, exact
Qwen/world Jacobian or completed non-scale research follows from this pilot.
