# Audited native design lifecycle UI v6

2026-11-01. `game-ui-v2/lifecycle.html` renders the completed v5
objective-conditioned institution-design campaign as a NOCTILUCA district. It
is a read-only evidence view, not a new optimization run and not a browser
adoption service.

## Evidence binding

`scripts/export_native_design_lifecycle_ui.mjs` reads the tracked audited
artifact `research/results/native-external-objectives-v5-a1.json` and writes the
portable browser snapshot
`game-ui-v2/public/data/native-design-lifecycle-v5.json`. The snapshot records
the audit artifact SHA256, source commit and input-manifest SHA256. The browser
contract fails closed if either loss arm, any of the three observed systems per
arm, the selected fingerprint, the later first-best tie, or the negative claim
boundaries are removed. Tests independently hash the source artifact again.

The view exposes both actual development paths:

- throughput: `[-1, -3, -3]` under `minimize -A`;
- net reviewed utility: `[0.70, 0.45, 0.45]` under
  `minimize 3.25A - Q + 0.05R`.

All six logical observations remain selectable. In particular, the later
two-node utility revision—`review-pricing` feeding `surplus-clearing` through
`publication-loss-offers-v1`—is visible with its executed source hashes, typed
ports, added/removed wires and full SystemSpec graph. It tied the first authored
revision at `0.45`; deterministic first-best selection therefore retained
revision 1. The view never relabels the later system as a provisional winner.

## Actor and truth separation

The UI explicitly separates the external Codex specialist institution designer
from the fixed local Qwen3:8B researcher model. Each candidate uses a separately
reset native world with fresh responses; it is not one persistent researcher
society. The author identity is
self-reported provenance, not authenticated provider identity. The five actual
physical worlds each contain five researcher agents and together produced 285
researcher responses; the shared baseline and
cross-scoring are not independent replicates.

Persistent boundary labels state that this is one development seed, not
held-out evaluation, scientific value, full-world differentiation, recursive
designer improvement or executed same-society adoption. The two LossSpecs are
illustrative engineering proxies. Changing the loss changes which executable
institution is designed; it does not establish that either proxy is desirable.

## Adoption action contract

The airlock is typed for `scienceutopia.native-society-design-session.v1` and
models `unavailable -> confirm-required -> pending -> completed|failed`.
Before dispatch, a live client must display and receive the exact staged
`confirmed_request_sha256`; a boolean confirmation is insufficient. The
controller binds that hash and request ID, rejects duplicate/reordered work,
keeps backend `pending` polls pending, and completes only when an `adopted`
response matches both identities and carries `verified_receipt=true` plus a
valid 64-hex durable migration-receipt hash. State and delivery decisions use
the session API's record-shaped contracts. The shipped page has no transport,
keeps confirmation and submission disabled, and reports `UNAVAILABLE`; this
historical v5 snapshot is not a live session and cannot install its selected
system directly.
The existing `/native-api/jobs` path creates fresh worlds and is deliberately
not reused as same-society adoption.

## Local verification

No inference or experiment job is started. Node exports the tracked snapshot,
Vitest checks its scientific and adoption boundaries, Vite builds the page, and
local Chrome CDP verifies both loss arms, all three stations, the two-node
protocol, English copy, disabled adoption, zero browser failures and no mobile
overflow.

- `game-ui-v2/screenshots/noctiluca-design-chronicle-v5.png`
- `game-ui-v2/screenshots/noctiluca-design-chronicle-two-node.png`
- `game-ui-v2/screenshots/noctiluca-design-chronicle-v5-qa.json`

