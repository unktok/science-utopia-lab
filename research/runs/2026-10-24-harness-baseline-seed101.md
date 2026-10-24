# Harness validation run: baseline / seed 101

## Identity

- Date: 2026-10-24
- Status: complete
- Purpose: seed-replicated experiment harness の end-to-end validation
- Study: `evaluation-v0`
- Study revision: `eadef0bb5a`
- Design: baseline (`dce5399cf6d0b`)
- Seed role: exploration
- Seed: 101
- Run ID: `opt-evaluation-v0-eadef0bb5a-smoke-exploration-dce5399cf6d0b-s101`
- Source commit: `71b81b545c20f02d319f4bd435c61fdd4c911b8c`

## Configuration

- Backend / model: Ollama / `qwen3:8b`
- RAG device: CPU
- Institutions / researchers: 2 / 10
- Years / conferences: 1 / 1
- Acceptance rate: 0.3
- Reviews per paper / reviewer capacity: 3 / 4
- Reviewer matching / policy: random / persona
- Funding slots fraction: 0.3
- Funding application cost / resubmission cost: 0 / 5.0

## Operational result

- Registry state: complete, return code 0
- Harness attempts: 1 complete, 0 failed
- Wall-clock: 1,424.32 seconds (23 minutes 44 seconds)
- LLM prompts: 76
- Prompt / completion tokens: 61,008 / 64,391
- Transport-level retries / failures: 0 / 0
- Papers / reviews / accepted: 2 / 6 / 1
- Active researchers: 10
- Final total resources: 960.0
- Native integrity check: passed, 0 failures

These are execution and activity diagnostics, not measurements of scientific or
public value. In particular, the observed 50% acceptance fraction has only two
submissions and must not be interpreted as evidence about the policy.

## Harness evidence

- The deterministic run ID was used consistently by the registry, attempt log,
  native manifest, docs directory, and checkpoint directory.
- The native manifest recorded `status=complete`, the exact source commit,
  resolved configuration, package versions, dataset revision, model identity,
  source-file hashes, token counts, and timestamps.
- The registry retained attempt-level wall time separately from final run state.
- The year-1 checkpoint, Parquet outputs, resource ledger, funding application
  log, simulation report, and integrity report were all produced.
- The aggregate report contains 1 complete and 9 planned runs. A second seed is
  still required before this becomes a replicated policy estimate.

## Quality observation: semantic regeneration

Funding proposal generation dominated the run. The simulator requested 26
applications initially and regenerated invalid outputs in batches of 10, 5, 5,
and 2, for 48 funding-application generation slots in total. The first batch had
10 proposals rejected by semantic validation because more than half of their
paper indices were invalid. This is distinct from the harness attempt count and
from transport-level LLM retries, both of which remained at one attempt / zero
retries.

The final funding evaluation and JSONL log contained 25 applications, although
the initial generation target was 26. Existing integrity checks do not flag this
difference. Before comparing funding institutions, the simulator should expose
semantic attempt counts, terminal validation outcomes, and explicit reasons for
every dropped application.

## Evidence hashes

- Run manifest SHA-256: `abe1cb5581445c038fb139ee48f7c5ed576ae387e8946ef599aee438bbf1e55f`
- Year-1 checkpoint SHA-256: `74f54bc33942aa2c2006d7788f078f8ba3bf48a52c691dadea7c2a72e13e0771`
- Registry report SHA-256: `a84dabfaf54a0d0cf6036841c15db863e251924e431b86ad37f9e1e6e29855e6`
- Attempt log SHA-256: `1971a90bd1eeb2ec9de51754342259e410cbcc790a10bae8d807d344072d9d08`

## Interpretation

The run validates the experiment-management path, not an objective function and
not a science-policy conclusion. The main immediate risks are compute cost,
semantic regeneration cost, and silent attrition between institutional stages.
They must be measured alongside policy outcomes so that an optimizer does not
prefer designs whose apparent performance comes from unobserved failure or
selective dropping.
