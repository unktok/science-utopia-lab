# Same-society native institution continuation v4

2026-11-01. A design change no longer requires throwing away the existing
research society and restarting it. This is institution migration, not a claim
that the designer recursively improves itself or that a change is beneficial.

## Executable API

`utopia.system.native_migration.migrate_native_design` accepts the current
`NativeScienceKernel`, a complete candidate `SystemSpec`, and the SHA256 of the
exact completed kernel inspected by the caller. The entire transaction is
preflighted before the kernel is changed. No mechanism, LLM or generated Python
is executed during migration. The next normal native year runs the new design.

The operation retains the society's existing agents, real projects, papers,
funding, histories, RNG, model and response-cache identity. It never edits those
objects or rewrites previous events. The original society binding stays the
founding identity; current designs are separately bound by the portable native
system contract and hash-chained migration receipts.

- Unchanged-node memory is retained. Changed stateful nodes require an explicit
  `preserve`, `reset`, or `{"replace": JSON_object}` action. New nodes use their
  declared initial memory. Generated-code memory must satisfy its state schema.
- Retired node memory remains archived in the source graph receipt.
- Pending messages survive with their old source, emission time and event
  references. Removing an edge does not retroactively recall an already sent
  message. Removed/incompatible receivers require explicit message-order/reason
  discard decisions; full discarded payloads remain in the receipt.
- Stale checkpoints, unknown implementations, invalid graph/queue/schema
  changes and active-year migration are technical errors, not loss penalties.
- Each receipt includes source/target SystemSpecs, graph snapshots, original
  event-prefix hash, parent kernel hash, boundary year, state/queue decisions
  and previous receipt hash. Old events keep their OLD design fingerprints;
  newly executed events use the new one. Restore verifies both epochs and
  each pure reconciliation, rather than relabelling history as the new design.

`install_recorded_native_proposal` closes an additional integration gap:
it retrieves an actual `native.system.design_proposed` event, verifies its
recorded hash and parent, compiles its exact patch and installs it in the SAME
society. The receipt binds the originating event. Selecting/installing that
proposal requires an explicit caller action; this function does not infer
merit, invent a loss, install arbitrary proposals on page views, or change the
declared objective. An external scheduler can call it at a completed boundary.

`commit_native_design(simulation, ...)` provides the durable enclosing-society
transaction, accepting either a candidate or a recorded proposal event. It
requires the just-saved native boundary and exact contract, prepares the new
kernel off to the side, archives the OLD complete portable checkpoint bytes
under their content hash (private local file), then atomically writes the
complete adopted society before replacing the live kernel. It does not call
checkpoint callbacks recursively. A failed write leaves the live society and
previous committed snapshot unchanged. The ordinary native checkpoint path
now refers to the adopted state; the previous state is recoverable from the
archive. `Simulation.load_checkpoint` validates the migration chain rooted in
the ORIGINAL configured design before allowing only its native fingerprint
to change in the contract. Other model/corpus/config/cache bindings still match
exactly. Cold restart requires no remembered migrated SystemSpec.

## Verification and scope

Actual `Simulation` integration QA runs six years with the real scientific
phases, papers and persistent response journal, while corpus/retrieval/HTTP
replies are scripted. At year1 a new messaging institution and protocol are
installed; at year3 its explicit state is preserved across revision. Researcher
requests after delivery contain its message; the exact society and RNG are
unchanged at both migration boundaries. Final portable kernel and full
Simulation resume preserve all three historical design identities and issue
no extra model requests. Another native integration closes recorded proposal
-> same-society installation twice. These are developer-scripted QA, not
Qwen-invented institutions or policy-improvement experiments.

Additional integration tests simulate shutdown immediately after a durable
adoption, then load with the ORIGINAL design and continue the same society.
Injected write failure proves no kernel/checkpoint partial adoption. Unrelated
configured worlds cannot adopt the saved lineage. Focused migration/native/
portable integration regression: 29 passed in70.23s.

Limits: completed annual boundaries only, one joint edit per boundary, same
system_id/founding attributes, data-only explicit state translation, and
existing registered native execution capabilities. The low-level kernel-only
function is intentionally nondurable; use `commit_native_design` for adoption
that must survive immediate shutdown. Browser migration controls, automatic
objective-conditioned proposal selection and actual improvement of the designer
remain separate work. Arbitrary new social concepts still need
executable consumers and persistent domain representations.
