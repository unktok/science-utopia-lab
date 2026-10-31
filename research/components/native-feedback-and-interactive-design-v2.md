# Native feedback, distribution gradients and interactive design v2

2026-11-01. [Protocol](../protocols/campaigns/native-feedback-breadth-v2.md),
[actual results and limitations](../results/native-feedback-breadth-v2.md).

## One native evaluation boundary, different proposal routes

```text
explicit LossSpec + current SystemSpec
       │
       ├─ source proposer: actual history → LLM plan/source → isolated probe
       ├─ graph proposer: named/joint source/protocol/node/edge/schedule patch
       ├─ gradient proposer: continuous-coordinate distribution draws
       └─ player: edit complete SystemSpec and loss → consent → durable queue
       │
       ▼
validated candidate → fresh original native researcher simulation
       → checkpoint-derived measurements → declared loss → saved observation
       → next proposal / distribution update / completed UI evidence
```

Fixed researcher weights do not imply fixed outputs. The real native simulator
generates subsequent language responses under changed institutional inputs.
Structural/source freedom and optimization method remain independent axes.
Technical validity, optimized loss, held-out metrics and optional promotion
policy stay separate; activity counts are diagnostics, not hidden rewards.

## Source revision

`utopia/optimization/native_feedback.py` restores hash-verified real native
checkpoints. Feedback contains prior losses, measurements, technical failures,
executed-node counts, delivered messages, author resources, first24 real paper
records and normalized per-author record counts. The optional planner saves a
structured diagnosis/algorithm/evidence record before source generation.

`NativeSourceRevisionProposer` accepts arbitrary standard-library Python logic
and JSON state within the existing observation/messages contract. This route
does **not** edit its ports, source-to-consumer attachment or new actor codecs.
Separate `llm`/`llm-intent` graph routes use the existing atomic design patch
boundary and now receive the same actual native feedback. Interface freedom
must not be confused with a successful native topology-invention result.

Generated code never executes on the host. It is validated and sent to the
existing pinned Docker image, with no network/host mounts/credentials. A real
checkpoint snapshot supplies the isolated probe, followed by a fresh native
world for loss. At most three technical source repairs are allowed by default;
an inert valid program is evaluated, not rejected or hand-fixed. Exact drafts,
errors, parent/history/loss bindings and successful source bytes persist.

CLI entry: `scripts/run_native_design_loop.py --proposer source-revision
--revision-node NODE --designer-plan --record-wire`, alongside required
`--system`, `--loss`, `--seed`, `--years`, `--corpus-years`, `--budget`,
`--output` and `--data-cache`. Run from a clean experiment worktree. The source
probe in the result uses an existing observer as a declared development input,
not evidence that the model invented its host attachment.

## Full-native cost gradient estimator

`NativeScoreFunctionSearch(..., sampling='antithetic')` draws paired ε and -ε
in latent design coordinates. For complete native costs it estimates
`mean((L_plus - L_minus) * ε / (2 * sigma))`. The existing bounded coordinate
transform maps these into actual SystemSpec numeric parameters. This estimates
the derivative of an expected smoothed design loss, not native pathwise autograd.
An iid leave-one-out baseline must not be applied to dependent paired draws.

The durable gradient campaign records draws, technical failures, complete
observations, estimator state and deterministic resume/replay. Invalid worlds
do not receive fabricated penalties or permit a numerical update. Equal costs
legally yield zero; no behavioral reroll is implicit. The demonstration script
is `scripts/run_native_feedback_gradient_probe.py`; general coordinates use
`scripts/run_native_gradient_loop.py --sampling antithetic` with an even count.
Both are separate from the existing conditional hard/soft tensor fit.

## Local game-UI execution

Build with `cd game-ui-v2 && npm run build`. From a **clean pinned** checkout,
start the loopback server:

```sh
PYTHONPATH=. .venv/bin/python scripts/serve_native_lab.py \
  --queue /absolute/local/queue --port 4591
```

Open `http://127.0.0.1:4591/native.html`. Select a recorded design, expand DESIGN
WORKBENCH, edit complete SystemSpec/LossSpec JSON, choose a development seed and
1–4-year horizon, validate, then explicitly consent and queue. Page viewing or
validation alone never starts inference. Changing inputs invalidates validation.

In a second terminal at the **same exact commit**, execute one job:

```sh
PYTHONPATH=. .venv/bin/python scripts/serve_native_lab.py \
  --queue /absolute/local/queue --worker-once --data-cache /absolute/corpus/cache
```

The worker exits after one job. Repeat to drain a queue; no unattended daemon is
installed. Queue source mismatch is a technical failure, not an automatic
source upgrade. For reproduction the committed UI example pins worker
`bceb48c`; a newer renderer may inspect that result without claiming it ran it.

SQLite stores frozen request/source identity and queued/running/complete/failed
states. An OS lock permits one worker; resume prioritizes an interrupted running
job and reuses its pending campaign. Active identical submissions are idempotent;
at most two jobs are active. GET progress reports saved checkpoint years, not
guessed completion or provisional loss. Completed measurements are rechecked
against the exact submitted loss before serving; the browser verifies exported
evidence and canonical SystemSpec hashes. Failure has no numerical score.

Host/Origin allowlists, an in-memory session token, bounded JSON bodies, static
directory containment, frame denial and no CORS reduce cross-site/local-browser
risks. Browsers cannot supply filesystem paths, shell commands or credentials.
Historical reserved held-out seeds cannot enter development jobs. Currently six
native domain measurements have loss adapters; unsupported metrics are rejected
as unimplemented, not silently fabricated. These are compute/schema/evidence
boundaries, not additional optimization policy constraints.

This is a trusted local development service, **not** an internet-exposed,
multi-user hardened code execution service. Do not bind it publicly. Docker
isolation is not proof against all runtime/kernel vulnerabilities. The UI edits
a new branch; it does not migrate an existing society or make arbitrary
protocols meaningful without actual consumers. Node/edge drag authoring and a
full management-game loop remain future work.

## Audit and browser reproduction

`scripts/audit_native_feedback_v2.py` supports `source`, `gradient` and `ui`.
Source/gradient require `--run` and `--loss`; later source probes also pass
`--require-wire`. UI uses `--run QUEUE --job-id ID` and reads the exact frozen
request LossSpec (do not substitute a same-ID file with different bytes).
The audit rederives domain measurements and scores rather than trusting JSON
status labels. Raw request journaling is opt-in and local, with no auth headers.
Keep prompts/responses private and out of Git; compact hashes/counts are tracked.

With task-owned local Chrome CDP9341, run
`cd game-ui-v2 && node scripts/verify-native-jobs.mjs --submit` to explicitly
queue one developer integration example; start the worker separately, then run
the verifier without `--submit` to load real completed evidence. This is not a
load-test command. Stop owned Chrome/server processes after QA, not Ollama or
unrelated user services. Local screenshots and reports are under
`outputs/native-jobs-browser/`.
