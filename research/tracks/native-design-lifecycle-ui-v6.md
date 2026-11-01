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
the session API's record-shaped contracts. The historical v5 panel has no live
adoption target, keeps its installation control disabled, and reports
`UNAVAILABLE`; selecting an archived system cannot install it directly. The
separate continuity console below provides transport only for a configured
actual same-society session.
The existing `/native-api/jobs` path creates fresh worlds and is deliberately
not reused as same-society adoption.

## Live same-society continuity spine

The same page now has a separate live-session console for the loopback-only
`NativeSocietyDesignSession`; it does not turn the historical v5 result into a
live adoption candidate. The console reads the session token and projection
from `GET /native-api/session` and `GET /native-api/society`. It renders each
completed interval as an online loss observation tied to its exact system
fingerprint, preceding migration and journal. These values compare consecutive
intervals of one continuing society. They are not counterfactual estimates,
independent replicates or evidence that a migration caused improvement. The
researcher model weights remain fixed.

When the live projection contains a staged request, the UI displays the exact
request, candidate and expected-checkpoint hashes. It enables confirmation only
after the operator pastes the identical request SHA256 and checks the explicit
authorization control. `POST /native-api/society/confirm` authorizes the worker
and returns `pending`; it never counts as adoption. The UI then polls
`GET /native-api/society/requests/{request_id}` and shows completion only for a
matching request ID and SHA256 with `status=adopted`, `verified_receipt=true`
and a valid durable migration-receipt SHA256. Pending remains pending, and
failed, mismatched, reordered or malformed responses fail closed. An absent
society API is shown as unavailable.

`?society=fixture` loads a separately labelled synthetic UI fixture. Its
confirmation controls are disabled and browser QA asserts that it sends zero
society POST requests. The fixture exercises interval, staged-request and
migration-lineage rendering only; its loss values and receipts are not research
evidence. The initial UI implementation alone provided no actual society result;
the later actual pilot is recorded separately below. Neither is evidence of
causal improvement or trained researcher weights.

## Local verification

No inference or experiment job is started. Node exports the tracked snapshot,
Vitest checks its scientific and adoption boundaries, Vite builds the page, and
local Chrome CDP verifies both loss arms, all three stations, the two-node
protocol, English copy, disabled adoption, zero browser failures and no mobile
overflow.

- `game-ui-v2/screenshots/noctiluca-design-chronicle-v5.png`
- `game-ui-v2/screenshots/noctiluca-design-chronicle-two-node.png`
- `game-ui-v2/screenshots/noctiluca-same-society-session-fixture.png`
- `game-ui-v2/screenshots/noctiluca-design-chronicle-v5-qa.json`

## Actual continuing-society browser proof

The [v6 a2 pilot](../results/native-society-v6-a2.md), clean source d68589f,
completes three actual intervals with loss `[0,-5,-5]` and two code/protocol/wiring
adoptions. The real loopback page sends one exact consent POST per boundary;
a separately resumed worker performs each migration. Final full reload verifies
both saved receipts and displays three intervals, without duplicate POST,
browser errors or desktop/mobile overflow. This is not fixture evidence, a
fresh-world comparison or causal benefit. Researcher weights remain fixed.

- `game-ui-v2/screenshots/noctiluca-same-society-v6-a2.png`: actual overview.
- `game-ui-v2/screenshots/noctiluca-same-society-v6-a2-panel.png`: readable continuity capture.
- `game-ui-v2/screenshots/noctiluca-same-society-v6-a2-qa.json`: actual checks.
- `research/results/native-society-v6-a2-ui-checksums.json`: original capture/raw hashes.

The owned server and Chrome are stopped; the temporary profile is recoverably
in Trash. Raw evidence and detached experiment source are unchanged. The final
integration's163 UI tests and production build pass; the existing large Phaser
replay-bundle warning is not misreported as a new build error or zero warnings.

