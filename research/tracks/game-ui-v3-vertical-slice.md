# Game UI v3: evidence-driven living arcology

Status: implemented and browser-verified on `track/game-ui-v3`.

## Slice

The same 48-second synthetic replay now shows three distinct researchers as
inhabitants of the 2D system rather than static tokens. Aya crosses the lab,
operates an instrument, writes, revises, receives funding, and reads a citation.
Mino enters a review cell, reviews a paper, and receives a policy change. Sol
enters the civic ledger, allocates funding, records a citation, and transmits
policy. The six flow grammars use distinct packet silhouettes, line cadences,
echo counts, endpoint portals, and labels.

The environment adds district platforms, skyline silhouettes, service rails,
conduits, signage, deterministic rain, and an ambient courier. These layers are
explicitly non-scientific atmosphere.

## Evidence boundary

`choreography.actions` is optional. Every action in the fixture is `derived`,
names one or more canonical event IDs, carries a derivation version, and is
validated in both Python and TypeScript. Real saved exports default to an empty
action list. If a replay does not supply an action, the renderer leaves the
researcher idle instead of inferring activity from role, balance, acceptance,
or any other state.

Clicking an active researcher or its action label opens the derived action and
its canonical source event. Flows retain the same evidence drill-down. Three
small institution-state marks are rendered only after their corresponding
canonical `paper.decided`, `resource.changed`, or `policy.changed` event and
click directly to that event.

## Determinism and motion

Researcher frame, position, packet position, trail, rain, and courier position
are functions of replay cursor. No wall-clock animation continues while paused.
Reduced motion selects the first representative state frame and a fixed packet
position. A repeated 1440x1050 Chromium capture at cursor 14,000 ms was
byte-identical.

## Remaining work

- expand each state from two to four or six frames and add directional walking;
- add a second laboratory and publication building to complete the original
  paper-to-publication-to-citation spatial loop;
- make intervention branches visually comparable without conflating them with
  optimization metrics;
- conduct external accessibility and pixel-art review.
