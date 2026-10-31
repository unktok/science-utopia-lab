# Native science kernel: containment, not a smaller replacement world

## Direction fixed with the user

The original research world is a **lower bound and one instance**, not the
desired ceiling. Abstract its execution without replacing researchers,
language, projects, papers, review, retrieval, funding or longitudinal memory
with numeric attributes. Smaller runs mean fewer actors/years, not less
expressive activity. Numeric program worlds remain method/unit tests only.

The target is a conservative extension: the default graph reproduces the
existing world, while alternative implementations, extra actor/artifact kinds,
new institutions and changed processes can inhabit the same execution engine.
No fairness/promotion veto is introduced. Choice of scientific loss remains
separate from technical execution validity.

## Implementation boundary

`NativeScienceKernel` binds the generic SystemSpec graph runner to a live
`Simulation`. Baseline nodes delegate to the existing phase methods; they do
not approximate or reimplement researcher decision rules. A private ephemeral
frame retains live ResearchDirection/domain objects within a year; graph
messages expose versioned JSON observations and full artifact content instead
of serializing model clients. Default control edges reproduce the old order.
Edges, latency, optional nodes and registered implementations are real design
objects. The baseline graph is a constructor, not the only accepted graph.

Separate native decision selection from publication commit so a replacement
institution can supply decisions while retaining actual conference, tracker,
RAG and downstream funding effects. The compatibility boundary requires real
paper identities and complete decisions, not a preferred acceptance rate.

Generic researcher-context delivery takes arbitrary typed graph payloads and
their causal provenance to real agents. Native prompts include those records;
zero records leaves original prompts byte-identical. Messages and queues are
checkpointed, so a new producer/consumer protocol can affect a later research
decision rather than merely decorate a replay.

Standard-library Python source remains isolated in Docker. It receives live
world records through declared ports and can connect to native consumers.
Trusted registry extensions can implement other capabilities; new mechanism
families are not limited to evaluation/funding. New actors require an explicit
serializer/behavior contract, not silent omission from a legacy roster.

## Verification gates

1. Default-off paths and portable contract shape remain unchanged.
2. Default graph and original coordinator produce identical scientific state,
   RNG state and model request payloads under the same recorded/scripted replies.
3. No phase or researcher behavior is mocked in the native lifecycle tests;
   only model/corpus transport can be explicitly scripted for deterministic QA.
4. A producer -> novel payload -> recipient chain changes real prompt input;
   removing the edge or delaying it changes when that input is available.
5. A replacement decision mechanism changes native publication state and
   subsequent researcher context without replacing the researcher world.
6. Checkpoint/resume preserves graph state, source identities, pending messages,
   actor context and canonical events; mismatched specs fail rather than vanish.
7. A clean, pinned local-Qwen run is separate evidence from scripted QA. An
   instruction arriving in a prompt is not by itself proof of behavioral effect.

## Differentiation: tied to this world, not a toy substitute

Native LLM calls, corpus selection, hard decisions and resource deactivation are
opaque/discrete nodes. Track those boundaries explicitly; do not claim autograd
through them. Tensor-backed local institutions may expose exact derivatives;
whole-path gradient claims must account for every node on the loss path.
Future surrogate/score-function/relaxation estimators must bind their training
and outer validation to native trajectories and the same scientific objective.
Changing to hand-picked numeric world laws is not native-world differentiation.

## Remaining scope

This first integration does not implement unlimited event scheduling, every
new actor behavior, empirical realism, or whole-world differentiation. Existing
research selection/corpus assumptions are preserved, not endorsed as sufficient.
The engine must support extensions beyond them; tests establish containment,
not that the original scientific ontology is final.

## Local transport note

Explicit thinking overrides now map to Ollama `/v1` `reasoning_effort`
(`none` for false, `medium` for true); an absent override retains the historical
body. This fixes a prospective execution setting, not old campaign evidence.
The local Qwen endpoint returned the requested JSON with six output tokens
under `reasoning_effort: none`. Primary provider implementation:
[Ollama reasoning mapping](https://github.com/ollama/ollama/blob/main/openai/openai.go).
