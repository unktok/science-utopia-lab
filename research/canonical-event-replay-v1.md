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
