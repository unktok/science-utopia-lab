# Qwen3-8B funding reliability probe

## Identity

- Date: 2026-10-25
- Status: complete for generation-interface validation
- Purpose: test the corrected funding prompt, validation path, trace schema and
  engineering gate against the real local model before a full simulator run
- Source commit: `aac514b`
- Model / backend: `qwen3:8b` / Ollama OpenAI-compatible endpoint
- Run seed: 20261025
- Concurrency: 2
- Study specification: `research/specs/study-v2-smoke.json`
- Planned study / revision: `evaluation-v2` / `54e12434e7`
- Reliability policy: `funding-pipeline-reliability` `1.0.0`
- Reliability policy SHA-256:
  `849098646e94fb98370be8d4f6df796d2d6ef04090e7fd6833590dfca858f7bd`

## Probe design

The probe exercised the production `funding_application_prompt`, Ollama
structured-output transport, `_generate_funding_applications_batch`, proposal
validator and `FundingApplicationTrace` on ten targets:

- 5 researchers with no past papers;
- 5 researchers with exactly 2 accepted papers;
- one matching funding program per researcher;
- the same retry limit and semantic validation path as the simulator.

This construction targets the v1 failure mechanism. It is not an institutional
simulation and does not estimate a scientific outcome.

## Result

| Diagnostic | Result |
|---|---:|
| Targets | 10 |
| Validated on first attempt | 10 |
| Generation attempts | 10 |
| Semantic-invalid attempts | 0 |
| Sanitized-reference attempts | 0 |
| Request-error attempts | 0 |
| Terminal drops | 0 |

All five zero-paper responses submitted an empty reference list. All five
two-paper responses submitted exactly two valid references. The measured rates
were therefore zero for semantic invalidity, sanitization, request error and
terminal drop. Policy 1.0.0 returned `state=pass`,
`disposition=eligible`, and `comparison_eligible=true`.

The same ten-case probe was first run from the prospective working tree and
then repeated from clean source commit `aac514b`; both runs produced the same
counts and reference-length pattern.

## Evidence and scope boundary

- Trace schema: `scienceutopia.funding_application_trace.v2`
- Clean-commit trace JSONL SHA-256:
  `6c3807164836566728488544c6273eeed945213db03079f165cdc88afbc84534`
- Local artifact directory:
  `outputs/validation/funding-reliability/aac514b`

The probe intentionally stops after proposal validation. Its trace summary
therefore reports submitted applications as not evaluated and must not be used
as full pipeline-conservation evidence. The reliability decision above uses
only the versioned generation-interface counts. A full v2 baseline run is still
required to validate evaluation, decision, allocation, objective measurement
and conservation together.

## Test evidence

- Funding + optimization suites: 134 passed, 1 skipped.
- Offline full suite: 602 passed, 2 skipped, 7 deselected, 7 failed.
- The seven failures are unchanged from the recorded pre-change baseline: six
  prospective-logging failures and the switching resume failure tracked in
  repository issue #8.
- Python compilation check passed for `utopia` and the modified tests.

## Campaign state and next gate

The v2 plan contains 5 designs × 5 exploration seeds = 25 planned runs; none
has started. The next authorized action is one full baseline run using seed 113,
the strongest v1 funding-generation stress case. The remaining 24 runs stay
planned until that run passes native integrity, funding conservation, objective
evaluation and reliability policy 1.0.0.
