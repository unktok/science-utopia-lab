# Native objective-feedback comparison control

Prospective implementation2026-11-07. `NativeAdaptiveDesignCampaign` accepts
`proposal_feedback='technical-only'` in blackbox mode, with no historical bank
or expectation estimator. The default `'loss'` adds no new binding field and
preserves legacy request/replay values. A changed policy cannot reopen a saved
campaign. Old experiments and failed certificates are not rewritten.

The prospective comparison's loss-visible arm uses `matched-loss`, which keeps
losses/measurements/optimizer feedback and loss-selected parents but matches the
exception-class-only technical error channel. The legacy default `loss` remains
unchanged. This prevents fuller runtime exception text being a second
unacknowledged advantage of the feedback arm.

The control uses a fixed initial parent and cost-independent uniform strategy
selection with chronological own-proposal history. A new allowlisted view
retains authored definitions/candidates, technical completion and exception
classes, but not measured values, losses, full error strings, raw outcome IDs,
loss-dependent digests, selections or update reports. The view's hashes and
ordinal identities are explicitly new view identities, not raw evidence IDs.

Full original observations, measurements, losses, messages and internal reports
remain in campaign state, subject to normal native observation validation.
Internal losses are not overwritten with null, and final objective-based
selection is not restricted by the proposal policy. Both the active prompt and
the virtual archive expose only the declared proposal view. Raw filesystem
paths are not archive fallbacks. Current bounded author context labels withheld
loss explicitly rather than displaying it as a technical null.

Noninterference is conditional on fixed authored proposals and technical
outcomes: perturbing numeric losses/measurements, native result metadata, raw
outcome IDs/hashes and loss-updated strategy data cannot alter the full control
request, prompt or virtual files. Technical success/failure itself is visible
and may be informative. Literal self-authored code/provenance remains own data.
This is not an adversarial callback security boundary or a zero-world-information
control. The comparison changes parent selection as well as scalar feedback.

The [finite prospective pilot](../protocols/campaigns/native-feedback-comparison-v1-a1.md)
uses the original research world, not a substitute simulator. Unit tests use
explicit synthetic numbers only for software QA, not scientific evidence.
