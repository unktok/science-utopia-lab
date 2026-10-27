# Canonical Event / Replay v1

This vertical slice is a read-only sidecar over saved ScienceUtopia artifacts.
It does not import the simulator or invoke an LLM.

## Inputs

- an end-of-year checkpoint_year_N.json or compressed JSON checkpoint
- an optional sibling resource_ledger.jsonl
- an optional sibling resource_balances.jsonl

## Contract

Every event uses scienceutopia.event.v1 and contains a deterministic content
id, canonical sequence, year, phase, event type, actor and artifact references,
payload, and logical source provenance. Physical paths and file timestamps are
excluded from event identity, so copying a run does not alter event hashes.

The first event vocabulary is deliberately small:

- agent.registered
- paper.submitted
- review.completed
- paper.decided
- resource.changed
- resource.balance_reported
- year.completed

The pure projector reconstructs agent balances and paper status from this
stream. It rejects dangling references, broken ledger transitions, mismatched
reported balances, and non-zero resource residuals.

## Sidecar command

Run the converter as a module and pass a checkpoint plus an output path:

    python -m utopia.replay.converter path/to/checkpoint_year_1.json \
      --output canonical-events.jsonl

This is intentionally not yet wired into simulation.py. Integration should
first compare sidecar events against multiple existing one- and four-year runs,
then make event emission native without changing event ids or replay semantics.

## Replay-view v2: an explicit truth boundary for the game

The canonical event schema and replay-view v1 remain supported without a
breaking change. Game UI v2 opts into `scienceutopia.replay-view.v2`, which
separates four kinds of information at the top level:

| Section | Authority | Meaning |
| --- | --- | --- |
| `canonical` | saved source records | canonical events, a fact index, and factual entity labels |
| `projection` | Python replay projector | authoritative world state at every event cursor |
| `choreography` | versioned deterministic derivation | placements, flows, and camera cues used to render the facts |
| `ambient` | presentation only | rain, traffic, crowds, and other effects with no scientific meaning |

Every fact index, projected frame, entity, choreography record, and ambient
record carries the following trace fields:

- `truth_status`: `canonical`, `derived`, or `ambient`;
- `derived_from_event_ids`: canonical evidence IDs (required for `derived`,
  empty for `ambient`);
- `derivation_version`: the exact choreography rule version;
- `logical_timestamp_ms` and `duration_ms`: replay time, not wall-clock time;
- `causal_parent_id`: an optional prior event or choreography record.

`stream_hash` continues to hash only the ordered canonical event dictionaries,
using `scienceutopia.python-canonical-json-sha256.v1`: UTF-8 JSON with sorted
object keys, no insignificant whitespace, non-ASCII characters left unescaped,
and non-finite numbers rejected. Presentation fields therefore cannot silently
change the identity of a run. Cross-runtime verifiers must implement this named
canonicalization exactly; switching to RFC 8785 would require a new algorithm
identifier and a separately versioned hash rather than redefining this one.
The export validator rejects a derived visual without event evidence, an
ambient record that cites evidence, unknown event references, unknown entity
endpoints, duplicate choreography IDs, and unsupported flow types.

The six flow types currently reserved by the visual grammar are `data`,
`paper`, `review`, `funding`, `citation`, and `policy`. A normal v2 export does
not invent any of them: the default choreography lists are empty until a
versioned derivation is supplied. In particular, an animated action that is not
supported by canonical data must remain under `ambient` and cannot be labeled
as a simulated scientific event.

Export a real saved bundle to the v2 envelope (with no fabricated flows):

    .venv/bin/python scripts/export_game_replay.py \
      path/to/checkpoint_year_1.json \
      --view-version 2 \
      --output replay-view-v2.json

## Synthetic vertical-slice fixture

`game-ui-v2/public/data/vertical-slice.replay.json` is an explicitly synthetic,
non-empirical contract fixture. It contains exactly three researchers, three
institution nodes, and one example of each of the six flow types so the
renderer can be tested before native simulation events exist for every flow.
Each flow derives from a corresponding synthetic canonical fixture event. It
must never be presented as an experiment, a policy result, or evidence about a
ScienceUtopia configuration. Decorative rain and courier traffic are isolated
under `ambient` with empty evidence lists.

Regenerate it deterministically with:

    .venv/bin/python scripts/export_game_replay.py \
      --vertical-slice-fixture \
      --output game-ui-v2/public/data/vertical-slice.replay.json
