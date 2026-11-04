# Why the staged designer inspected without editing

The investigation identifies a real generation-interface defect before any
claim about Qwen3:8B capacity. The declared edit schema accepts arbitrary JSON
values, but the local backend compiles an empty schema into an **object-only**
grammar. Direct string, numeric, boolean, array and null edit values are therefore
unavailable to constrained generation even though the host validator accepts
them. In instructed controls, the same fixed model correctly edits with JSON
mode or a small typed schema, but not the original schema. The historical
alternating-read loop is also invisible to the existing progress detector.

These are concrete engineering defects and local causal evidence, not proof
that they alone explain every historical action. No production fix, new native
world, new institutional improvement or larger model is part of this diagnosis.
Main remains at `32a8c18`; all changes are local diagnostic code and research notes.

The [machine-readable audit](staged-designer-diagnosis-v15.json) binds raw
replies, exact wire payloads, plans, static transitions, grammar observations
and unchanged historical evidence. Repeated cold analysis is byte-identical.

## The historical failure was not an optimization conclusion

Both independently published inventories still match: a1 has153 raw files;
a2 has209. A1 produces64 inspections of complete built-in phase nodes (48 review,
16 close) and never finishes. A2 produces60 inspections and4 finishes. Its
inspection values are all `{}`:31 review parameters,28 submission parameters,
one open parameters. There are51 revisits to an already observed unchanged
address/value across the four a2 sessions. No action reads literal institution
source, edits, configures a distribution or validates a changed draft.

The index already lists nonempty, editable nodes including selection code,
feature-extraction code, tensor policies, processes and domain capabilities.
The designer instead keeps alternating two empty built-in phase parameter
objects. This is unproductive navigation, not evidence that the parent is
optimal. A valid finish means the submitted system passes technical checks;
it does not prove the model compared alternatives or used its loss effectively.

Context overflow and a fixed-response cache are not supported explanations:
historical prompt counts range6594–10688 against a32768-token setting, all64
replies complete, and each session uses16 distinct recorded seeds. The prompt
contains the exact own prior loss in each G1 request. This proves availability,
not comprehension. The historical server version and exact HTTP request bytes
were not archived; those limits remain explicit.

## The generation language is narrower than the accepted edit language

The host operation schema at
`utopia/optimization/native_authoring_ir.py:35` uses `value: {}`. Under the
declared JSON Schema, an empty schema accepts any JSON value. Host tests confirm
strings, numbers, booleans, null, arrays and objects are all valid operands.
The staged designer passes that same schema to Ollama's `format` field.

The actual local llama-server compiler returns these rules for all four
add/replace branches, including stable-ID and full-document variants:

```text
operations-item-0-value ::= object
operations-item-1-value ::= object
operations-item-3-value ::= object
operations-item-4-value ::= object
```

Thus the correct instructed control below is legal to the host but cannot be
generated under those rules because its operand is a string:

```json
{"tool":"edit","operations":[{"op":"add","path":"/metadata/diagnostic_probe","value":"control"}]}
```

This is not merely a model choosing the wrong value. Five direct grammar
metadata queries use an empty token prompt with `n_predict:0`; every response
reports zero evaluated and zero predicted tokens. The reduced `value:{}` query
also compiles to `object`. Explicit string, explicit JSON-type-list and explicit
`anyOf` controls admit strings as expected. These are compiler-language checks,
not extra model generations or a production patch.

The observed local compiler build reports `b1-0f3a71be1`, with Ollama0.33.3.
For external implementation context, Ollama's
[tagged transport](https://github.com/ollama/ollama/blob/v0.33.3/llm/llama_server.go)
passes the schema to llama-server, and the release's declared llama.cpp pin
[b10760 converter](https://github.com/ggml-org/llama.cpp/blob/b10760/common/json-schema-to-grammar.cpp#L1018)
contains the same empty-schema-to-object branch. The local extracted grammar,
not an assumption that these build identities are identical, establishes the
defect here.

This does **not** make every institutional change impossible. A whole enclosing
object can contain nested scalar values; splice explicitly accepts source text;
new whole nodes and typed distribution coordinates have other routes. It does
break straightforward arbitrary scalar/string/array assignments and creates
an undeclared restriction that is absent from the host's design language.
It remains in main's unchanged operation schema; role/ABI/history additions
did not repair it.

## Controlled edits separate model ability from the original grammar

After the first30 diagnostic replies, a separately declared12-call control
uses two fixed historical per-arm seeds, two contexts and three grammars. The
task explicitly specifies the harmless metadata edit above; it is a syntax
test, never autonomous invention or scientific optimization. Model digest,
sampling options and task stay fixed within comparisons.

| Context | Original full schema | JSON mode | Small edit-only schema |
|---|---:|---:|---:|
| Isolated149-token interface task | 0/2 correct | 2/2 correct | 2/2 correct |
| Original dense institution context | 0/2 correct | 2/2 correct | 2/2 correct |

With the full schema, isolated controls change the requested string operand
into an object, `{"control":"string"}`. Dense-context full-schema replies are
incomplete, containing non-JSON continuation. The other8 controls return the
exact requested edit. These pairs identify a local grammar/interface obstacle;
they do not prove general invention or that a repaired designer improves loss.
The edit-only schema also constrains the task, so JSON-only successes are the
important unconstrained-schema positive controls.

The invalid long-context outputs have `done:false`, no stop reason and no final
token metrics. They must be called incomplete, not2048-token truncations or
successful edits. Their transport time is known; missing token counts are not
imputed as zero.

## The loop detector and instruction placement

`turn_control` compares consecutive identical action hashes at the same draft.
The review/submission alternation resets its counter to1 on every turn. All
four historical a2 sessions therefore receive zero repeat notices. Unit tests
reproduce both this blind spot and the detector's working consecutive case.
This is a proven **failure to detect** the loop, not proof of why it began.

Historical SYSTEM text calls observed strings data, while the actual task,
tool instructions and ABI sit inside user JSON. Moving the trusted constants
to SYSTEM is sensible separation, but source-ordered paired probes show it is
**not sufficient**: both arms still request the same empty review parameters.
Combining that change with an explicit objective reminder, full observed-read
memory and a nonconsecutive progress notice instead makes both arms inspect
`world.selection/parameters`, which contains real code and image parameters.
This is useful navigation, not an authored institution. The bundled comparison
does not distinguish the separate contributions of memory, warning and goal
salience. No continuation or native loss is inferred from a one-step response.

## A replay confound discovered and preserved

The first20 single-step probes read sorted JSON journals and send sorted-key
payloads. Their baseline produces an inspect action with `text` but no `path`,
unlike the historical reply. Source reconstruction then restores the original
schema property order while changing no semantic JSON values. Both source-order
baselines reproduce the historical action. The exact differing wire bodies and
their hashes are recorded. Canonical semantic hashes alone do not preserve
this operationally relevant distinction.

Consequently, the first phase's role/memory/thinking/temperature comparisons
are not labelled faithful historical reproductions. The change in current
behaviour caused by schema order is real in these pairs, but sorting did not
cause the original experiment's failure: the original request used source
order. The remaining10 calls of the original30-call diagnostic budget were
reallocated to this confound test before any reserved continuation; no such
continuation ran. The additional12 controls had a new prospective plan and
user-facing notice rather than silently extending a closed experiment.

## Why the previous tests did not catch this

The existing unit/integration tests feed valid SCRIPTED tool responses to the
host interpreter and assert outbound schema fields. Those checks verify literal
editing, validation, replay and provenance, but do not establish equivalence
between host JSON Schema acceptance and the real backend's compiled generation
language. Another mismatch is visible in the original schema: only `tool` is
required, and all tools share one bag of optional fields, whereas the host
enforces per-tool required and allowed fields. A grammar-valid inspect with
`text` and no `path` is therefore rejected by the actual interpreter.

Treating loop plumbing and native completion as the operational milestone was
accurate for that narrow milestone, but insufficient diagnosis of authoring
quality. This investigation should have preceded claims that the designer was
ready for meaningful unrestricted institution search. No novelty or loss-gain
gate is needed to test whether a legal instructed edit can even be generated.

## Accounting and next engineering tests

The three diagnostic phases preserve42 dispatch intents and42 known HTTP
replies, including6 incomplete responses. Recorded transport intervals sum
277.31s; known token totals are249035 input and2277 output, with token metrics
missing for6 replies. These are diagnostic costs, not native experiment samples.
There are five additional zero-token grammar metadata queries, zero native
worlds, zero generated-source executions and no production changes. Two cold
analysis passes agree byte-for-byte, binding113 raw artifacts and unchanged
historical153/209-file inventories. Related diagnostic/staged-author tests pass81
checks; they are not a model-performance or production-fix claim.

The next changes to implement, after this diagnosis, are:

1. Make the model-facing generation language match legal host values. Explicit
   JSON type unions already compile correctly in the zero-token check; an
   explicitly selected JSON-mode transport with the existing strict host
   validator is another candidate, not a hidden fallback.
2. Align per-tool required/allowed fields between generation and validation;
   keep unrestricted institution code/graphs, not a reduced policy catalogue.
3. Give the author durable semantic read memory and notices for repeated
   unchanged addresses, including cycles. Do not ban retention or force novelty.
4. Test primitive legal edits and a sustained original-institution design trace
   before spending another long native campaign. Keep technical completion,
   objective-directed design, measured improvement and scientific benefit separate.

The exact sufficient cause of the first inspection choice and the reliability
of autonomous institution invention after repair remain open. There is now
a concrete, reproducible edit-language defect to repair, rather than grounds
to declare that8B models cannot perform the task.
