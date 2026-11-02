# V9 a2: separate server envelopes from actual response semantics

Fixed prospectively before a2 inference. Preserve a1 source
`d5b08d64193c32bf05dec95e54ba53d2f1b8cab9`, all completed/partial worlds,
full raw wire/SQL/checkpoint/code/completion receipts, and its strict-comparator
failure. Do not overwrite/relabel them as a2 or hide their actual Qwen budget.

The original comparator hashes full ChatCompletion JSON across worlds. Actual
Ollama responses contain server-created timestamps, random request IDs and
cache-usage counters. These necessarily vary even when the researcher receives
the same content. Existing scripted FakeHTTP QA uses stable envelope metadata
and missed this production-format bug. This is a control-comparison software
defect, not a scientific fidelity failure or an unfavorable institution result.

Only cross-world response equality changes: compare the same actual input
payloads and the EXACT complete `choices` (messages/content, finish reasons,
tool/refusal fields if present), excluding no choice content. Continue to
integrity-check every full original response `data_sha` and bind the raw prefix
envelope hashes separately in each per-world proof. Server model/source/corpus/
seed/checkpoint/cell remain fully bound. No differing native researcher text,
paper, reviewer, resource, pre-intervention scientific observation, or model-visible
rubric field is masked. This is not a stochasticity workaround or prefix replay.

Do not revise the original v9 protocol. A separate a2 source/output runs the
same six planned controls, objective, original 2year/5author/seed42/four-year
corpus, unchanged public rubric and exact candidate rule. Its plan additionally
binds this amendment hash. The maximum physical engineering budget becomes
the preserved three a1 calibration worlds plus six a2 worlds =9; no a1 outcome
selects a2 controls, model, temperatures or loss. If a1 stops earlier, report
the actual lower count. No held-out seeds or population scale-up is added.
No replacement for a poor valid scientific outcome is allowed. Any content or
pre-intervention scientific drift still fails closed and is reported.
