# Constitution-bound trace validation: baseline / seed 103

## Identity

- Date: 2026-10-24
- Status: complete
- Purpose: complete the second preregistered baseline seed and inspect run-to-run variation
- Study / revision: `evaluation-v0` / `6fcbf8bae1`
- Design: baseline (`dce5399cf6d0b`)
- Seed role / seed: exploration / 103
- Run ID: `opt-evaluation-v0-6fcbf8bae1-smoke-exploration-dce5399cf6d0b-s103`
- Source commit: `999e276e9b9d2c3ca9206992dcd0bffc427f59b5`
- Metric Constitution SHA-256: `0b9cb462d1a161514eda80033b3e62a5360d14dc455b2c03f8689fefdb389f05`

The preregistered exploration seeds are 101 and 103. Seed 102 was not part of
this campaign and was not added after observing results.

## Operational result

- Backend / model: Ollama / `qwen3:8b`
- Registry state: complete, 1 attempt, 0 failures
- Wall-clock: 1,481.28 seconds (24 minutes 41 seconds)
- LLM prompts: 86; first-attempt successes: 86; transport retries / failures: 0 / 0
- Prompt / completion tokens: 70,423 / 64,334
- Papers / reviews / accepted: 3 / 9 / 1
- Active researchers / final total resources: 10 / 960.0
- Native integrity check: passed, 0 failures

## Funding-application conservation

The trace summary passed:

```text
28 targets
  = 26 validated + 2 terminal semantic-validation drops
26 validated
  = 22 submitted + 4 declined_by_agent
22 submitted
  = 22 evaluated
  = 22 decided
  -> 3 funded
  = 3 allocations recorded
  = 3 allocations applied
```

- Generation attempts: 52
- Semantic-invalid attempts: 26
- Request-error attempts: 0
- Reasoned terminal drops: 2
- Agent-declined submissions: 4
- Prompt-free trace events / submitted application records: 159 / 22

The two drops exhausted all five generation attempts and were recorded with
agent, program, attempt history, and semantic-invalid reason. They are not
unexplained attrition. The integrity rule therefore passed while preserving the
fact that the targets did not reach evaluation.

## Baseline seed comparison

| Diagnostic | Seed 101 | Seed 103 |
|---|---:|---:|
| Papers | 2 | 3 |
| Reviews | 6 | 9 |
| Accepted | 1 | 1 |
| Funding targets | 26 | 28 |
| Validated | 26 | 26 |
| Agent declines | 1 | 4 |
| Terminal drops | 0 | 2 |
| Submitted / decided | 25 | 22 |
| Funded / allocations applied | 3 | 3 |
| Generation attempts | 48 | 52 |
| Semantic-invalid attempts | 22 | 26 |
| Wall-clock seconds | 1,433.25 | 1,481.28 |

The pair demonstrates material path variation under an unchanged institutional
design. It does not provide a variance estimate with useful precision, and the
activity fields are not optimization objectives. In particular, the stable
accepted and funded counts must not be read as evidence of policy robustness:
the denominators and pre-decision paths changed.

## Evidence hashes

- Run manifest: `d4348134f213e12a43098f1b7b1111e05a8cbcb90d711317e835d3fc87acf2a7`
- Native integrity report: `d85facc90318ecf08ae2fe9cef296c4ef242bc5c34151019c81829c9e5c28554`
- Funding trace JSONL: `8fabe11377add5dc7bc71721faf70dfbbc1f55f1ac655628d5d82d08a26e35b4`
- Funding trace summary: `462d357a18ffa32399c671fc14a91c5a6fe0ffec88255faa4b24dcc5ff7c9cdd`
- Two-run registry report: `c1efb710657d038f8f7beac4d7c87aa2bdbd048a7a0e0fd9a4d9c13c883e00db`

## Interpretation and next gate

Both baseline seeds are now complete and auditable. The campaign is 2 complete /
8 planned. This clears the operational gate for running the four Sobol candidate
designs on the same two seeds. It does not yet clear the scientific gate for
ranking those candidates: the current objective metrics remain provisional, the
constitution asks for at least five runs for uncertainty summaries, and no
confirmation seeds have been run.
