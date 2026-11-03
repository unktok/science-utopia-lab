# Stable-ID native authoring interface

This prospective interface addresses ordinary editing and feedback failures.
It is not evidence of useful institutional invention, scientific value, or model
competence. Historical v14 a1 requests, failed outputs, costs, source and null
slots remain unchanged. No historical candidate is repaired or labelled valid.
The implementation was developed in a separate feature worktree and verified
only with SCRIPTED outputs; no model or native-world calls were made for it.

## Exact address contract

`utopia/optimization/native_authoring_ir.py` defines optional
`StableIDAuthoringProtocol`, schema `scienceutopia.native-stable-id-authoring.v1`.
The output keeps `operations, factors, continuous, rationale, optional logits`.
Nested operation, selector, choice, support and coordinate schemas reject unknown
fields and incorrect types. Existing SystemSpec ID syntax still applies; there
is no fixed institution catalogue or semantic source whitelist.

An operation may select a mechanism by its exact stable ID and use a JSON
pointer local to that mechanism:

```json
{"op":"replace","selector":{"mechanism_id":"authored-id"},
 "path":"/parameters/authored-numeric-field","value":0.25}
```

For whole-mechanism replace/remove, the local path is `""`. Adding a new
mechanism uses explicit full-document add and a fully authored node value.
Omitting `selector` leaves the unrestricted existing full-document JSON-patch
escape, including array insertions/removals, new mechanisms, ports, protocols,
wires, schedules, process delegates and metadata. No missing source, parameter
use, schema object, wire or graph edit is supplied by the compiler.

The compiler resolves each exact ID against a JSON shadow after preceding
explicit edits. Missing/ambiguous IDs, malformed pointers and scalar traversal
fail precisely. There is no fuzzy ID match, guessed index, string-to-schema
conversion, inferred code rewrite, support filtering or identity fallback.
Only the completed transaction is validated by the existing atomic SystemSpec
patch compiler. Literal source remains data, parsed for its existing AST/ABI
contract and never imported/executed by this compiler.

Code source must be a literal string of 1–65536 UTF-8 bytes. Port/schema
containers and individual port schemas remain literal JSON objects, not encoded
strings. Executed code nodes, including process delegates, must use the exact
operator sandbox image. Existing full graph, artifact, source and process
validation remains in force; none of these technical checks asserts usefulness.

## Factors and continuous paths

Stable factor-choice selectors resolve after the explicit base and earlier
selected choices. The compiler uses the existing complete conditional-support
enumeration, capped by its existing 4096-assignment preflight bound. It retains
every declared factor, choice, support rule and logit. It translates addresses
and then uses the unchanged `GeneratedMixedDesign`/factorized kernel.

One backend choice stores one literal operation list. If that same choice would
resolve to different array pointers across reachable prefixes, compilation
rejects it with a branch-dependent-pointer diagnostic. An author may explicitly
declare distinct conditional choices/paths. Full-document paths retain their
literal index semantics, including when different branches put different nodes
at that index; the compiler never guesses intended node identity.

Continuous coordinates may use the same selector plus a local field pointer,
or an explicit full-document pointer. The target must already contain a finite
number in every reachable structure. Source text, booleans, schema strings and
objects are rejected. Bounds must be finite and ordered, mean finite, sigma
finite and positive. The resolved pointer must be identical across reachable
structures; otherwise the unchanged backend cannot represent that coordinate
and compilation rejects it without implicit gradient/coordinate transport.
The host does not invent a parameter or modify source to read it.

## Diagnostics and prompt view

`AuthoringIRDiagnostic` carries structured technical errors including stage,
operation index, authored/resolved path, deepest existing prefix, first missing
segment, available keys, actual owner ID/implementation and expected/actual
types where relevant. Source errors include byte count or AST line/column;
wrapped code identifies both outer and executed owners. Branch errors retain
the assignment and previous/current resolved paths.

The deterministic parent path catalogue groups exact local pointers and JSON
types by mechanism ID, implementation and global pointer. Source descriptors
include byte lengths and explicit exclusion from numeric coordinates; other
text, numeric and boolean fields have their exact JSON types. Global state and
metadata use full-document pointers. The declared summary treats structural
arrays, node ports and contract schemas as typed containers, whose complete
children remain in the full parent. It never truncates based on byte count.
The catalogue duplicates no literal source bodies and is stable under JSON
object-key reordering. Grouping avoids repeating node IDs and implementation
labels for every field. The full current parent remains
in the model prompt, together with all own scalar outcomes, null failures and
updates. The catalogue describes the parent rather than prescribing designs.

For this protocol, a failed generation also archives each attempt's exact raw
IR, raw-IR hash, started/completed receipt hashes and detailed technical errors
inside its malformed `generation_failure` definition. Later own-history prompts
expose those technical errors and exact operation addresses/receipt hashes.
They represent prior literal operands by type/byte/hash descriptors. Explicit
`prompt_view_metadata` declares omission of prior candidate bodies, other
failed-IR fields/rationales/literal operands, and provider message/transport
bodies; exact content remains in the archived request, campaign failure and
author journal. Other-arm data is not introduced, and prompt overflow still
fails explicitly rather than silently truncating history.

A read-only size check on the recorded a1 initial parent, without compiling or
repairing any historical candidate, produced a 23,804-byte catalogue and a
66,329-byte stable prompt, below the existing 240,000-byte explicit guard.
These are serialized byte counts, not a provider tokenizer/context guarantee.

## Journal and compatibility boundary

`LLMVocabularyGenerator(..., protocol=None)` remains the legacy default.
`compile_authored_output` and `build_prompt` remain callable with the a1 format.
The optional protocol supplies schema, prompt construction, compilation and a
binding identity. Stable protocol journals additionally bind schema,
instructions, deterministic compiler and legacy-adapter source hashes.
Changing protocol/settings/source identity cannot resume the old generation.

The production helper `make_local_vocabulary_generator` now defaults to
`protocol='stable-id-v1'`; explicit `protocol=None` selects legacy. This default
is a prospective source change for integration after the historical writer is
closed. Historical a1 audits must use their frozen source/report environment;
this interface does not claim byte equivalence to that historical adapter.

The returned definition adds `authoring_compiler` provenance containing exact
raw IR and translated output, both hashes, per-operation address maps,
coordinate maps, compiler identity and reachable-assignment count. This is an
auditable deterministic syntax transport trace, not semantic source invention.
Cold replay recompiles raw output to validate the same complete definition;
rehashing a forged raw/translated trace does not make it accepted evidence.

SCRIPTED tests cover arbitrary literal graph/source transport without execution,
sequential and reordered addressing, missing/duplicate IDs, pointer escapes,
schema/source/AST/numeric diagnostics, hidden delegate image checks, factor and
coordinate branch stability, explicit conditional support, full-document escape,
deterministic prompt/catalogue reconstruction, exact journal replay/tampering,
failed-IR feedback and unchanged legacy constructor/compiler behavior.
