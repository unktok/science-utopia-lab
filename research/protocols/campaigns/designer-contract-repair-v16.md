# Designer contract repair V16: prospective technical verification

2026-11-04. User asks to fix the diagnosed interface defects thoroughly and
prevent recurrence. This is not a larger scientific optimization campaign.
Historical a1/a2 and all V15 diagnosis outputs remain frozen at their own
sources; no failed dispatch, seed retention or cost is retroactively repaired.

## Implementation boundary

- Arbitrary edit operands explicitly enumerate all JSON types. No institution
  policy catalogue, novelty requirement, fairness constraint or merit veto.
- Sender and host share a per-tool contract. JSON mode is selected explicitly
  before dispatch; there is no error-triggered grammar fallback or source repair.
- Exact UTF-8 POST bytes, byte hash and host-schema hash are archived. Sorted
  journal dictionaries are not a substitute for the actual serialized request.
- Bounded literal read memory preserves resolved addresses, slice/value hashes
  and small observed values. Larger/older bodies are explicitly omitted/stale.
  Nonconsecutive unchanged-address revisits generate information, not a ban.
- Production factories, CLI campaign entrypoints and search-enabled server
  startup require a successful local real-backend certificate. Before each
  production author POST, it is cold-replayed and backend metadata rechecked.
  Missing/failed/incomplete/stale/source/backend/image-mismatched evidence stops
  dispatch. Direct model construction is reserved for calibration/testing.

## Finite real-backend budget, declared before dispatch

Fixed Qwen3-8B digest from the existing operator binding, temperature .2,
thinking disabled, context 32768, at most2048 output tokens, zero retries.
Read-only backend version/model GETs are additional metadata, not generations.

1. Staged interface calibration: maximum13 POSTs. Eight exact operand controls
   (integer, fractional number, boolean, null, array, nested object,
   Unicode/multiline literal source string, integer above2^53) against the
   actual original-world parent context. Then a continuous five-step session:
   inspect actual source → append an explicitly harmless comment via splice →
   inspect changed source → static validate → explicit finish.
2. One-shot transport compatibility: maximum8 POSTs, same typed controls and
   original-world context, exact existing one-shot envelope. A separate
   certificate; no claim the one-shot designer is a reliable autonomous planner.
3. If staged calibration passes, two separate unforced authoring sessions may
   each use at most8 calls at2048 tokens under the original throughput and
   reviewed-production objectives. No host-written design, forced edit, native
   world or adopted institution. This checks sustained planning separately from
   the instructed interface controls. Retention/failure is reported honestly.

Maximum37 new POST attempts in this revision. Stop a calibration at its first
failure/unknown result; never automatically replace calls or raise limits.
Fresh output directories, clean committed experiment worktree and exact source
pin required. All received/partial/unknown replies remain charged and archived.
Zero generated-source execution and zero new scientific worlds in this protocol.

## Certificate semantics and renewal

Operator-owned local certificate, not remote/cryptographic attestation. Verify
the original raw HTTP body, exact wire, JSON type/value and interpreter receipt
for every case; a `passed` flag alone is insufficient. Runtime fingerprints cover
all `utopia/**/*.py`, including compiler/graph/ABI/discovery. Model digest,
Ollama version, image identity and protocol must match. Lifetime24h; future-dated
or expired certificates fail closed. Recalibration is explicit, finite and logged.
Tests/docs changes alone do not invalidate runtime fingerprints. Raw prompt data
and certificates stay in ignored outputs, never sent from browser paths.

### Forward-only correction after the first actual call

At source `0077334`, staged-a1's first typed control returns an inspect action
instead of the requested integer edit. Gate closes after one charged reply;
no remaining controls or unforced sessions dispatch. This is not a pass. The
calibration task precedes the generic author protocol/objective in SYSTEM and
therefore conflicts with later generic instructions. Move the Python-caller
task to the end of trusted SYSTEM authority; never promote observed strings.
Keep a1 intact. A fresh source-pinned a2 may use13 staged +8 one-shot controls;
reduce optional unforced planning from8 to7 calls per arm. Total across both
revisions is at most1+13+8+14=36, within the original37 bound. No retries, refunds
or new scientific worlds. This amendment precedes any a2 dispatch.

Passing proves those literal interface controls and source compilation only.
It does not prove novel useful institution invention, loss improvement, generic
8B reliability, or scientific validity. Scaling is not the remedy for a broken
interface; a valid interface is not evidence of a good research result either.

### Second forward-only correction, before a3

At `b405127`, a2 again closes after its first integer control: a valid inspect,
not the requested edit. Reordering SYSTEM authority alone is insufficient;
normal optimization narration still asks for a different task. Both one-call
failures remain distinct. A3 uses explicit Python-owned interface-control
conversation mode: no scientific loss/task narration, the actual full original
parent and completed receipts as observed data, and an exact literal editing
task. Same fixed model, JSON wire, options, response schema and pure interpreter;
no fallback based on an error. Production factories remain in `author` mode.
The continuous source-edit control checks that declared task only. Ordinary
unforced planning is still a separate test and must not be inferred from it.
Before a3 dispatch, the shared budget is2+13+8+14=37 maximum POSTs. No increase.

## Operator commands

Use the approved uv-managed environment and a clean pinned checkout:

```sh
<python> scripts/check_designer_contract.py run \
  --provider-config <operator-config.json> --request <original-author-request.json> \
  --output <fresh-calibration-directory> --protocol staged-v15
<python> scripts/check_designer_contract.py verify \
  --provider-config <operator-config.json> \
  --certificate <calibration-directory>/certificate.json --protocol staged-v15
```

Supply `--designer-preflight <certificate.json>` to campaign/server CLIs. Renew
with a fresh evidence directory after runtime/backend/model change or expiry;
never edit a certificate's source hashes, timestamp or pass flag to bypass it.
