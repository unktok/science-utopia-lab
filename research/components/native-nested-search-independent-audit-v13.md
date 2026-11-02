# Independent finite nesting and native capability audit v13

`scripts/analyze_native_nested_search_v13.py` reads a closed or explicitly
incomplete v13 output. It never executes a simulator, model, generated source or
container, and verifies a before/after inventory of every raw input. Output must
be outside the raw run. Historical auditors and historical raw data are unchanged.

The exact two LossSpecs, original five-author/two-year/four-corpus-year setup,
fixed Qwen, scientific seed 42, source commit, model/corpus hashes, instructions,
learning rate .1 and fixed `[2,1,1]` stage counts are checked. Every native runtime
Python source blob and the reused evidence helpers are compared to the actual
experiment pin. New analysis helper hashes are separately recorded, not silently
attributed to an older experiment source. Source checks include the new routing,
plan-provenance, kernel, simulation and optimizer implementations.

The auditor replays the saved finite controller without persistence. Only G0/G1
have external authoring requests; the same-vocabulary forward is not fabricated
as another external response. Own history, exact parent/ties, vocabulary identity,
draw RNG/index/likelihood, all costs and the one estimator receipt are replayed.
`native_nested_estimator_audit_v13.py` independently derives scalar Gaussian,
Bernoulli and masked conditional categorical likelihoods/scores without autograd,
then checks the two-draw LOO gradient and .1 step. It checks that the next fresh
singleton uses the exact resulting distribution and G1 has no additional update.
No gradient through generated source, Qwen responses or native world is claimed.

Completed native evidence independently re-extracts loss from actual checkpoint
PaperTracker records, not institution-written final scores; all worlds are also
cross-scored under both exact losses. Checkpoint source/design/model/corpus/seed,
annual event prefixes, actual original HTTP response journals, source/container
receipts, executed wires and actor histories are joined by reused physical
evidence primitives. A narrow v13 adapter supports lawful zero-code worlds
without manufacturing an empty code journal; all other old physical rules are
preserved. This is data verification, not native-world re-execution.

`native_capability_effect_audit_v13.py` additionally reconstructs each complete
captured original research plan plus exact generated amendments, verifies the
final plan hash and submitter order, and joins source events and available wires.
For generated plans/amendments/routing commands it verifies actual isolated code
output and container receipts. Native output values are captured by the pinned
handler; the audit does not regenerate an unobserved LLM decision. Missing old
full-plan context is not retrospectively invented or relabelled complete.

Review routing joins the native pre-review snapshot, exact original submission
fields, explicit routing command and original native task identities to actual
archived integer-parsed reviews, original response-cache item/attempt/seed IDs,
wire prompt hashes, structured output schemas and parsed response hashes.
Original selection can legally change status, reviews, final score and append
review history after the input snapshot; those later fields are recorded, and
the earlier review-history prefix must remain unchanged. Captured reviewer
eligibility comes from the source-pinned native snapshot, not a counterfactual
pre-review world reconstruction. Empty task lists retain zero actual reviews.

Failures remain null. A generation-failure sentinel is one recorded stage, not a
synthetic world, and records its scheduled slot count (G0 may consume two).
Actual drawn worlds, consumed slots, physical replies, partial directories,
failed source versions, all exact ties and unsuccessful revisions remain visible.
Undeclared worlds, response reuse, changed raw bytes, forged likelihoods/updates,
future/other-arm history, hidden promotion requirements and unsupported claims
fail closed. Cross-scores reuse development checkpoints, not held-out metrics;
neither an executed mechanism nor a nonzero update proves useful invention,
method superiority, causal science-policy benefit or scientific value.

CLI:

```
.venv/bin/python scripts/analyze_native_nested_search_v13.py \
  --run /absolute/immutable/native-nested-search-v13-a1 \
  --expected-source <actual 40-character source commit> \
  --output research/results/native-nested-search-v13-a1.json
```

`--allow-incomplete` is required for an interim report, never an implied final
result. Repeating the read-only audit on unchanged evidence is byte-identical.
