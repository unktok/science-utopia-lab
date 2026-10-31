# Generated implementation-code mechanisms v1

## Scope

The earlier numeric program world invents expressions within a fixed AST,
five input vectors and four effects. It does **not** generate arbitrary
institution implementations. This track adds a different, black-box execution
route: local Qwen3-8B writes actual Python functions with branches, loops,
helpers, standard-library imports, arbitrary JSON memory, and new output
artifact schemas. The host supplies compatibility ports, not the algorithm.

Implementation: `utopia/system/code_mechanisms.py`, `code_proposals.py`,
`utopia/optimization/code_lab.py`, `scripts/run_code_mechanism_lab.py`.

## Interface, not a rule catalog

Each artifact contains `schema`, `label`, `source`, `inputs`, `outputs`, and
`state_schema`. Port values are JSON Schemas. The model chooses its algorithm,
internal state layout, and additional named output schemas. Existing nodes can
use established compatibility ports while newly invented messages use new
artifact types. Source must define `step(context)`; there is no arithmetic
operator whitelist or predefined template menu.

The context has `period`, `phase`, deterministic `random_seed`, caller
`parameters`, own checkpointable `state`, and `inputs`. Inputs map ports to
lists of records with `payload`, actor/artifact IDs, origin and emission period.
The function returns exactly:

```python
{"outputs": {"my_port": [{"payload": {"any": "structured content"},
                          "actor_ids": ["researcher-1"],
                          "artifact_ids": ["artifact-1"]}]},
 "state": {"arbitrary": ["JSON", "memory"]}}
```

All declared output ports appear, possibly as empty lists. Finite JSON,
declared port schemas and state schemas are checked before graph state commit.
Schema references are disabled, including nested definitions: no network schema
lookup. A contract failure is technical invalidity, never a numeric penalty or
an implicit fairness/promotion criterion.

## Isolation and evidence

No model-produced Python is imported, evaluated or executed on the host.
The executor resolves an already installed Docker image to an immutable ID,
then uses no network, no host mounts, a read-only root, non-root user,
no capabilities, no privilege escalation, bounded CPU/memory/processes/tmp,
wall-time and captured-output limits. It never downloads an image or falls back
to host execution. The container is ephemeral; only its exact generated name
is removed after a call. Host observations/loss and credentials are not provided
to generated runtime code. [Docker run reference](https://docs.docker.com/engine/containers/run/).

Source/context/result hashes, image ID and execution timing are recorded.
Canonical graph events omit timing so deterministic source can reproduce event
and checkpoint hashes. The runtime seeds Python `random` with node/period/world
seed, independent of candidate fingerprint for common random numbers.
Arbitrary source can still use nondeterministic facilities, and containers are
not a proof against kernel exploits; this local prototype must not be exposed
as a public untrusted-code execution service. Replay tests detect the exercised
source's nondeterminism, not all possible future executions.

## Small closed loop

`propose_local_code` receives task, compatibility schemas and prior measured
observations. It emits source and additional schemas, then executes a caller
probe. Actual syntax/schema/runtime/production errors are returned for up to
three model repairs. Raw requests, responses and model digests are retained;
there is no successful fixture substituted for a failed model response.

The demonstration wires:

1. Deterministic paper/review fixture -> generated institution.
2. Generated decisions -> the actual production `PaperTracker` adapter.
3. Invented output artifacts -> a generic checkpointed artifact ledger.
4. Host measures accepted/rejected records, gives source + observation to Qwen,
   and asks for a revised implementation under each of two opposite losses.
5. `Suggestion` / `Observation` retain the complete fingerprint-bound
   `SystemSpec`, scalar loss, parent observation and execution provenance.
6. Independently replay revised source and compare uninterrupted execution to
   split checkpoint/resume. Frozen source can reproduce without a model query.

Losses are deliberately gameable negative accepted/rejected record counts.
All-accept and all-reject are legal. This is an integration test, **not** a
recommendation for publication policy, an informative scientific objective,
an equal-budget optimizer comparison or evidence of new scientific discovery.
The first prototype uses a fixed graph harness and fixture workload, not the
full original longitudinal Qwen researcher society. Extra artifacts are stored,
not yet consumed by newly generated researcher behaviors.

## Reproduction

```sh
.venv/bin/python scripts/run_code_mechanism_lab.py --output outputs/code-mechanism-v1
.venv/bin/python scripts/run_code_mechanism_lab.py \
  --proposal-input outputs/code-mechanism-v1/result.json \
  --output outputs/code-mechanism-v1-reproduction
```

Run recorded experiments from clean pinned source; dirty development requires
an explicit flag and must not be described as pinned experimental evidence.

## Not solved by arbitrary code generation

This route is black-box. Python loops, hard branches, sorting and string
generation are **not** automatically differentiable. The existing tensor-world
route remains separate, with finite rule/order banks and hard projection.
No original Qwen token generation has been placed in autograd. No raw source
code is executed by the browser game. See the complete
[non-scale limitation inventory](../audits/non-scale-limitations-v1.md).
