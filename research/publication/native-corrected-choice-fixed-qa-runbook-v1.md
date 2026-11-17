# Corrected fixed-evaluation public QA: prepared command, not an execution

November17UTC. The active original scientific job must finish first. This
runbook does not reserve hardware, attest unused scientific conditions, prepare
a real evaluation plan or authorize an external service. Existing
[fixed-evaluation protocol](../protocols/campaigns/native-corrected-choice-fixed-evaluation-v1.md)
and [software scope](../components/native-corrected-choice-fixed-evaluation-v1.md)
remain unchanged.

## Preconditions to recheck immediately before launch

- Original writer30048 and supervisor29982 have normally exited, with unchanged
  source/plan and original paired closure. A progress file or HTTP200 is not
  completion. Do not kill/pause scientific or other-project work to obtain room.
- Inspect host-wide CPU/inference activity, including in-process MLX models.
  A separate worktree or absence in an Ollama-only filter does not prove hardware
  isolation. Do not run this independent native/Docker QA during real inference.
- The dedicated reader `/Users/shiro/unktok/dev/science-utopia-lab-experiments/native-corrected-choice-data-v1-a1`
  is clean at `fb87f6afc5f8bf9628f45999571b0aedb1b5a5eb`. Never change that HEAD
  while its two data continuations or this QA are live. Required test/module
  files were checked after actual full worktree checkout, not an empty index.
- The original workflow binding exists at the path in the command below; its
  fileSHA is `f2a12bf41b8cd0ff790f441c2db2cdb2b2082828210c86c1ac9808f860a13d3e`
  (verified November17). Recheck it; do not substitute another model or plan.
- Both explicit external destinations below were absent at preparation. Recheck
  absence, including the basetemp/JUnit targets, before making the exact parent.
  Preserve any failure. Do not overwrite, clean or silently reuse an earlier run.

## Prepared command — NOT RUN

Use the approved Python; no package install or Apple Python is needed. The
command deliberately sets both named public-QA flags and uses external retained
raw/test destinations. These are software seeds42/43003/43011, not the proposed
scientific evaluation conditions83003/83011.

```sh
cd /Users/shiro/unktok/dev/science-utopia-lab-experiments/native-corrected-choice-data-v1-a1
test ! -e /Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-check-v1-a1
test ! -e /Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-qa-v1-a1
mkdir /Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-check-v1-a1
PYTHONHASHSEED=42 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' \
HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_PUBLIC_QA=1 \
SCIENCE_UTOPIA_PRIORITY_FIXED_PUBLIC_QA=1 \
SCIENCE_UTOPIA_WORKFLOW_PLAN=/Users/shiro/unktok/dev/science-utopia-lab-experiments/native-longitudinal-comparison-64k-v1-a1/outputs/native-longitudinal-comparison-64k-v1-a1/plan.json \
SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_QA_EXTERNAL=/Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-qa-v1-a1 \
/Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python -B -m pytest -q -s \
  tests/reports/test_native_corrected_choice_fixed_public_v1.py --maxfail=1 \
  --basetemp=/Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-check-v1-a1/pytest-tmp \
  --junitxml=/Users/shiro/unktok/dev/science-utopia-lab-exports/native-corrected-choice-fixed-public-check-v1-a1/pytest.xml
```

Execute only after the preconditions pass. In a shell, ensure a failed preflight
stops the dependent launch; the listed lines are not a failure-tolerant script.
If a target already exists, inspect/preserve it and deliberately name a new
attempt rather than invoking pytest's basetemp cleanup on prior evidence.

## Evidence required after the actual original test exits

Require one passing case with zero skips/errors/failures, normal command exit,
and a clean unchanged reader. Keep exact JUnit and raw `verification.json` or
`stopped.json` plus all component/native/cold records. Inspect the actual report:
both15-label scopes/reference bank, intentional development null, all30 logical
evaluation rows, all120 seedwise contrasts,2–30 literal-identity-shared fixed
physical jobs, zero designer generation,900s/zero-retry scientist transport,
paired matching native audits/costs/readouts and no new calls during cold reads.
HTTP, corpus, upstream provenance and child supervision are explicitly SCRIPTED;
outer subprocess routing is not established by this in-process public-path test.

No scientific result or unusedness claim follows from QA. Only after normal
original development/readout closure may the real banks be frozen and strict
all-path v4 inventories establish an explicit local unused-condition scope at
both preparation and dispatch. Never reselect policies using those outcomes.
Interpret the scientific value and costs before a new real dispatch; this
runbook is not automatic scale-up or a publication-readiness certificate.
