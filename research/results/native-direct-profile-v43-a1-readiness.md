# V43 error recovery and actual technical readiness

The combined fixes pass the source-pinned regression suite and fresh local
designer controls. This is a technical readiness result, not a new scientific
optimization experiment or evidence of improved institutions.

## What changed

- Add an explicit plain function-JSON history profile. Preserve authored strings,
  rejected actions, errors, receipts and charged steps; do not repair responses.
- Add opt-in `plain-function-direct-v43`, requesting `think: false` for both
  designer roles. Bind it through plans, actual payloads, certificates and replay.
  Legacy defaults remain unchanged; researcher agents remain Qwen3-8B.
- Derive actionable missing-field diagnostics from the actual SystemSpec types.
  Report paths and operation ownership without supplying missing model values.
- Remove redundant forced Docker removal after successful foreground `--rm`
  execution. Keep forced cleanup for unsuccessful/live clients, independently
  attempt bounded local cleanup, and preserve primary errors and interruptions.
- Include original technical failure details in native integration assertions;
  retain full-test artifacts in an explicitly created output directory.

The [eight-call diagnostic projection](native-designer-error-diagnostics-v42-a1.json)
records the preceding fixed-frame measurements: legacy history completes 0/3
versus plain history 3/3; disabling thinking turns the reproduced thinking-only
length failure into a complete valid plan. These small probes are not general
reliability or design-quality estimates.

## Source and software checks

Frozen source: `e920af700f8e4a3b8b93ef385344c6614d6b1e7a`, tag
`diagnostic/native-direct-profile-v43-a1`. All 262 staged driver/runtime/helper
source blobs verify. Relevant optimization, report, model-provenance, tensor,
generated-code and Docker integration checks pass: **1,604 passed, 2 optional
skips, 756.00 seconds**; process 82928 exits 0.

JUnit `outputs/native-direct-profile-v43-a1-verification/broad-committed-source-r2.xml`:
`64dc7b1b1290be4dc5f9dd559a3f28f7b8218a9e0aaf7d88bee55485c32dac31`.
Preserve the earlier real Docker cleanup failure and the separate first V43
invocation's missing-basetemp-parent setup failure. Neither is overwritten or
counted as a successful run. Full details are in the
[logbook](../logbook/2026-11-06-native-direct-profile-v43.md).

## Fresh actual controls and cold replay

Process 55722 exits 0: **28/28 technical controls pass** at the unchanged local
`qwen3.6:35b-mlx-64k` provider and Ollama 0.33.3. All planned cases exactly match
the earlier readiness inputs; all responses are newly acquired. Scope:
`execution-readiness-v39`; profile: `plain-function-direct-v43`.

Certificate content SHA256:
`b545654cf8e23d1ca7d2ca29bc947ced278ec511f5bd3f1c83d12f1ee53c4f3d`.
Runtime binding:
`dcf908313a9fc97b15eb06e94b72bdc4e3e1ff4b71945462c5fc0cf0d7bf5617`.
The CLI's final original-response cold replay passes. A separate process 47522
also verifies the same certificate without any generation POST.

Exact copies: 26/28. `sequence-edit-fields-source` and
`sequence-write-code-file` remain recorded diagnostic mismatches, not silently
normalized. Actual received values pass schema, interpreter and static checks;
replay reconstructs original HTTP actions and receipts. Both roles request
no thinking; all 28 responses have no nonempty separate thinking field and no
invalid thinking-field type. This describes observed metadata, not internal
model computation.

Costs: 28 actual generation POSTs; all token records known; **238,090 input /
1,292 output tokens**. Adapter time: **144.19644129415974 seconds**; transport
time: 143.2559530804865 seconds. Zero retries, generated-source executions or
native scientific worlds. Readiness controls apply only nonexecuting interpreter
edits/static validation. The software suite separately executes bounded fixtures.

Raw evidence: `outputs/native-direct-profile-v43-a1-preflight`, 58 JSON files.
Filename-to-file-SHA256 inventory digest:
`cd7429788e8a7f6410d39d4ed8a9304d8fdfa8d75611a660bfcdccaad8f2e0c2`.
Certificate file SHA256:
`9bb34b6e4d75a5c26017c776ab1797b5c3a9ed432b04281ff644fedc6855f841`.
Raw outputs stay outside Git. Old failed certificates and original V39 outcomes
remain unchanged. A later scientific run must explicitly choose the profile
and satisfy its current source/runtime/backend/certificate gates; this result
does not automatically dispatch another campaign.
