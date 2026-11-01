# Staged source-authoring ABI clarification

`NativeABIRegionProposer` in `utopia/optimization/native_abi_region_proposer.py`
inherits the existing staged proposer's complete constructor/controller API.
It overrides only `_draft`: both phase bindings receive the distinct schema
`scienceutopia.native-region-proposal.staged-abi-v5`, and the source-phase
prompt receives mechanical execution-ABI explanations. Historical staged, a2,
and original v5 classes, compilers and probe implementations remain unchanged.

The source reply maps **node ID to Python source**. That packaging does not add
a node-ID dimension inside an installed function's context. Each individual
function receives `context['inputs']` directly keyed by its own **input port**;
the value is a list of transport envelopes. Literal paths are derived from
the chosen plan, e.g. `context['inputs']['dossier']`, and conditional first
payload paths are displayed with an explicit nonempty-list precondition.

For every chosen node and every observed period, the amendment routes the
already projected external boundary values through that node's explicitly
selected input references. Resulting partial context snippets are flat port
dictionaries and are labelled `actual-external-projection`. Internal upstream
programs have not yet executed: their ports appear separately as
`schema-only-not-an-observation`, never as invented payloads or fabricated
empty lists. Ports merging external and internal sources are explicitly marked
partial, preserving only actually available external examples.

Native-world shape explanations distinguish the dictionary
`payload['conferences']` from its list
`payload['conferences']['conferences']`. A conference's `submitted_papers`
is a list, `reviews` is a paper-ID-to-review-list dictionary, and each review
is a dictionary containing its score. These are container/ABI facts, not a
supplied acceptance rule, threshold, institutional implementation or code body.

All generated source remains exact model output. Chosen graph, interfaces,
loss, bounded repair budgets, archived drafts, chronological full native probes
and fresh-world evaluation remain the parent's implementation. Source/plan
prompts and receipt bindings are deterministically reconstructible through the
new subclass. An amended campaign must be separately registered and pinned;
this does not permit extra hidden drafts in an exhausted historical attempt.

Tests use explicit software fixtures, including a source with the erroneous
extra node-ID lookup that really raises a native-probe `KeyError`, followed by
an exact fixture-generated correction. They are not a successful LLM result.
