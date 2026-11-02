# Gradient estimation for open scientific institutions: Parmas references

Recorded 2026-11-02 following the user's recommendation of Paavo Parmas.
Scope: first-pass reading of primary publication abstracts and the author's
research website, not a completed full-paper reproduction or software adoption.
The supplied Google Scholar page was not retrievable; publisher/arXiv pages
and [the author's website](https://paavo5.github.io/) were accessible.

## Relevant primary work

1. Parmas and Sugiyama, **A unified view of likelihood ratio and
   reparameterization gradients**, AISTATS 2021.
   [Publisher](https://proceedings.mlr.press/v130/parmas21a.html).
   Treats LR and RP as ways of tracking probability-mass movement and
   characterizes a family of combined estimators. Useful for separating the
   desired expected-loss derivative from the mechanism used to estimate it.
2. Parmas and Seno, **Proppo: a Message Passing Framework for Customizable
   and Composable Learning Algorithms**, NeurIPS 2022.
   [Publisher](https://papers.neurips.cc/paper_files/paper/2022/hash/bbc9d480a8257889d2af88983e8b126a-Abstract-Conference.html).
   Automatic propagation packages learning computations as composable
   propagators, including LR, RP and total propagation. It motivates an
   estimator interface rather than requiring every institution to expose an
   ordinary automatic-differentiation graph. We have not adopted Proppo.
3. Parmas, Seno and Aoki, **Model-based Reinforcement Learning with Scalable
   Composite Policy Gradient Estimators**, ICML 2023.
   [Publisher](https://proceedings.mlr.press/v202/parmas23a.html).
   TPX combines LR/RP estimators with inverse-variance weighting. The reported
   benefits concern the paper's model-based RL tasks, not our LLM society.
   Our v11 control-variate estimator is NOT a reproduction of TPX.
4. Onoda, Parmas, Yaguchi and Matsuo, **Does "Do Differentiable Simulators Give
   Better Policy Gradients?" Give Better Policy Gradients?**, ICLR 2026.
   [Primary preprint](https://arxiv.org/abs/2604.18161), version 2 dated
   2026-10-24. Examines nonsmooth dynamics, estimator switching and per-step
   variance control. Motivates checking estimator behavior rather than
   equating a differentiable implementation with an effective optimization
   method. Findings from robotics do not establish the dominant issue here.

## Connection to the native design problem

Let a declared design distribution sample a discrete institutional edit and a
continuous latent variable, jointly denoted X, and let the original native
world produce loss L. Conditional on a fixed generated vocabulary, the target is

    J(theta) = E[X ~ q_theta, native randomness][L(X)].

If the native execution's conditional distribution has no additional direct
theta dependence and the usual differentiation/support conditions hold,

    grad J = E[L(X) grad log q_theta(X)].

This differentiates the sampling distribution, not arbitrary Python source,
Qwen tokens or the world transition. Gaussian latent samples can be mapped
through a fixed sigmoid to bounded institution parameters without computing a
derivative of native loss. The current executable version's categorical factors
and Gaussian means have explicit likelihoods; unknown source-generation
probabilities remain outside this conditional estimator.

For a control variate c fixed before the current batch, when its expectation is
tractable under q_theta,

    grad J = E[(L(X)-c(X)) grad log q_theta(X)] + grad E[c(X)].

This is an identity under the same conditions even if c predicts native loss
poorly; variance reduction is NOT guaranteed. Treat model fitting and the
expectation correction separately. Current-batch fit, incompatible coordinate
transport, silent rejection of invalid draws and missing likelihood terms can
invalidate an unbiasedness claim. Technical failures remain null observations,
not invented scientific losses. A finite executed batch is not proof of
unbiasedness, native derivative fidelity or a useful institutional discovery.

## Implementation priority

Use the existing free-code/native-world boundary, not a new simulation.
Implement the conditional estimator, a prior-data-only fit, explicit correction,
durable reports and analytical tests. Run a fixed small native pilot and report
all observed outcomes. Retain represented-world gradients as an optional
additional route; do not make whole-world differentiability the milestone.
