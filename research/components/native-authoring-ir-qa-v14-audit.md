# Separate stable-ID authoring QA audit

`scripts/analyze_native_authoring_ir_qa_v14.py` is a read-only auditor for the separately frozen two-slot engineering QA, not the closed eight-slot A1 aggregator. It binds the prospective manifest, exact numeric browser JSON wire strings, single submission/queue row, request-specific queue plan and world, stable-ID protocol source, full author prompts/raw replies/IR, unchanged campaign checkpoint effects, and scientist/designer costs separately.

Compiler replay changes addresses only: the auditor independently checks authored operands, support, rationale and weights, including JSON numeric types. A missing completion consumes an attempt with unknown reply/server processing/cost; it never fabricates a response or redispatches. Closed worker receipts and logs can be joined with repeated `--worker-receipt` arguments. Queue reads use SQLite read-only connections; controller/queue constructors are not called by the auditor. Raw evidence inventory must remain unchanged across each audit.

SCRIPTED tests cover the actual adapter and queue with the real stable-ID compiler, failing no-world factories, interrupted resumption and rehashed tampering. They are software checks, never actual scientific observations. The actual-only 5.5-inch figure reports null loss/no compiled design honestly and keeps unknown author cost explicit.

The QA changes source, prompt, authoring IR and UI together. Neither this audit nor a successful roundtrip establishes improvement over A1, controlled optimization performance, scientific value, or institution adoption. Preparation can issue read-only tags/image/corpus checks; its no-calls label does not mean zero HTTP.
