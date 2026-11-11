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
The initial bank covers `world.selection` and `native-feature-extractor` in
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
The model-facing editor does not yet advertise or call this API. Connecting
the tool, its literal cold replay and fresh real-backend readiness is next;
no new institution or optimization benefit follows from this component alone.
The live fixed-candidate evaluation remains unchanged at frozenf1f8ddf.
