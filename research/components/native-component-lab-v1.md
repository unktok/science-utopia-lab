# Component tests on recorded native inputs

The optional component lab tests arbitrary model-authored Python artifacts
against literal inputs recorded in the original researcher world. It uses the
existing no-network container executor, never host Python execution, a new
numeric world, or a scientific loss oracle. Candidate algorithms need not
reproduce the original component's output; only the declared JSON contract is
checked. Full native evaluation is still required to measure policy effects.

## Finite API

`NativeComponentLab` binds a source revision, fixture provenance, immutable
fixture bundle hashes, runtime image, execution timeout and at most eight probe
attempts. `probe(artifact, fixture_id)` retains literal intent before dispatch,
then the returned output/receipt or raised error. Invalid fixture requests and
contract failures consume a slot; there is no host code repair, alternate
fixture, automatic retry or budget reset on reload. A pending intent blocks
further probes. Cold replay validates hashes, output contracts and image/input/
artifact/result receipts without executing code again. Raised errors are
preserved observations, not a claim that a remote container completed.

The trusted orchestrator supplies `DockerCodeExecutor` with an already local,
pinned image and a declared timeout. The JSON model cannot choose an executor,
host command, filesystem path or new image. Unit tests inject a fake executor
and do not establish real container or model behavior.

## Developer fixtures

The staging script reads the unchanged original671436a source and the full
stopped-prefix audit. It selects only completed developer references:
open-seed, reviewed accept-all and typed one-reviewer accept-all, all seed61001.
The [actual staged bank](../data/native-component-fixtures-v1/README.md) covers24
inputs for `world.selection` and `native-feature-extractor` in
their actual recorded years. Bundle hashes, source/system/run identity,
unique native-event attribution and the complete historical raw inventory
must match. No unused-evaluation world is read and no failed-call input is
guessed. The raw bank stays in ignored output; a compact origin manifest can
be retained in Git.

These contexts describe executions under reference institutions, not states
visited by an arbitrary new policy. Source or upstream-interface changes can
invalidate their relevance; passing the test cannot certify a full mechanism
graph or future native trajectory. The bank is optional and does not constrain
new nodes, ports, topology, timing or policy merit. Fixture bundles alone are
not source audits: the staging attribution is necessary for a native claim.

## Integration status

The API and staging guards pass24 fake-executor checks. The native attempt
recorder and existing physical/simulation guards separately pass35 checks at
5cc8493. These suites overlap and are not independent scientific samples.
The [optional post-edit adapter](native-post-edit-feedback-v1.md) now connects
the lab to the model-facing editor, with scripted repair-loop and cold-replay
checks. Fresh real-model readiness and the actual finite assay remain next;
no new institution or optimization benefit follows from this component alone.
The live fixed-candidate evaluation remains unchanged at frozenf1f8ddf.

## Finite real container diagnostic

A separate three-call diagnostic fixes one actual developer selector input:
open-seed, seed61001, year1. It tests the original artifact, retained T/fixed
G1 selector, and retained E/fixed G0 selector, in that order. These two failed
submissions are selected before this diagnostic, not after observing new results.
The original pinned local image and15-second executor limit remain in force.
If the baseline does not return, stop without replacement; otherwise preserve
both candidate results even if the expected failure is not exercised. There
are no LLM calls, new scientific worlds or source repair. Reproducing a code
exception on one recorded input is not reproducing the full original world.

[Actual three-call result](../results/native-component-lab-real-diagnostic-v1.json)
at clean3c0ba8c: the baseline returns the exact historical output; the retained
record-envelope failure raises; the retained float-index failure returns on
this empty paper batch. Its faulty `values[i][0]` expression is inside the
unentered record loop. No replacement input was tried. Two new-process cold
replays agree, with execution explicitly disabled. The source corpus and active
evaluation are unchanged. Future model-facing tests need a predeclared suite
covering empty and nonempty native states, not a one-input pass/fail promise.
