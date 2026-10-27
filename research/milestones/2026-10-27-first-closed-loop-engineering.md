# Milestone 3 — First real result-dependent closed loop

**Date:** 2026-10-27
**Outcome:** completed

Science Utopia Lab has completed its first model-backed, result-dependent
black-box optimization campaign. The end-to-end path is now demonstrated:

1. freeze a versioned engineering loss, design space, seed partition, budget,
   source commit, and protocol tag;
2. persist optimizer suggestions before execution;
3. run three Qwen3-8B simulator seeds per suggestion;
4. reject only technically invalid observations;
5. aggregate measured loss and return it through `tell`;
6. derive an adaptive third suggestion from the lower-loss initial observation;
7. survive controller restart without changing identity or history;
8. stop at the declared budget while leaving held-out seeds untouched.

Nine runs completed on their first attempt. The adaptive candidate tied its
parent on the coarse engineering loss; it did not improve it. This is an
engineering success and an objective-resolution warning, not a science-policy
result.

Canonical records:

- [protocol](../protocols/campaigns/first-closed-loop-engineering-v1.md)
- [machine-readable result](../results/first-closed-loop-engineering-v1.json)
- [interpretation](../results/first-closed-loop-engineering-v1-interpretation.md)
- artifact manifest: `research/artifacts/first-closed-loop-engineering-v1.manifest.json`
