# Objectives and losses

This directory defines what an optimizer directly tries to improve. It is not a
registry of every quantity the simulator can measure.

- `losses/`: executable and versioned optimization objectives
- `catalog/`: literature-traceable future candidates; not executable losses
- `landscape/`: construct audits and objective graphs for future campaign design;
  report-only and never an executable registry
- `design-spaces/`: parameters and mechanisms that may change
- `constitutions/`: optional normative commitments for campaigns that explicitly
  choose them, including the prospective evidence-gated ObjectiveSpec compiler

Historical objective documents remain at their original paths and are mapped in
[`../INDEX.md`](../INDEX.md).
