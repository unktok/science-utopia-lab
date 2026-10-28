# NOCTILUCA research-arcology hub v1

## Purpose

The replay city, system-design sandbox, and optimization mission control are
three parts of one game experience, but they do not share one scientific truth
contract. The hub makes that distinction spatial: each mode is a separate
district behind an explicit door.

| District | Destination | Truth boundary |
|---|---|---|
| Evidence Quay | commit-pinned completed campaign replay | `VERIFIED REPLAY` |
| System Foundry | structure-only SystemSpec console | `SYNTHETIC SANDBOX` |
| Orbital Control | timestamped optimization registry projection | `VERIFIED SNAPSHOT` |

The presentation-only transit deck is not a fourth evidence source. It does
not load, join, summarize, cache, or reinterpret data from any destination.

## Isolation contract

`src/arcologyNav.ts` contains only destination labels, URLs, artwork paths,
and presentation copy. `src/hub.ts` does not import replay types,
`missionContract`, `systemSandbox`, or scientific state. It performs no
network request. The only optional shared state is
`sessionStorage["noctiluca.presentation.lastMode"]`, whose allowed value is
one of `replay`, `sandbox`, or `mission`.

Each destination retains its independent loader and fail-closed validation:

- replay reads replay-view v2 and verifies its canonical stream;
- sandbox reads only the synthetic SystemSpec contract;
- mission control reads only its hashed registry projection.

The shared rail inspects URL source selectors solely to avoid a false truth
label. `?replay=synthetic` becomes `SYNTHETIC REPLAY`, and
`?source=synthetic` on mission control becomes `SYNTHETIC UI FIXTURE`.

## Spatial UX

The hub is a cyberpunk night transit deck with three institution-scale
terminals, route lights, district signage, gates, courier drones, and a
presentation-only player marker. All artwork uses existing hand-authored
NOCTILUCA fixed-palette production SVGs or CSS geometry.

- Arrow left/right moves between native anchor doors.
- Enter opens the selected district.
- Alt+H returns to the map; Alt+R/S/M opens a district directly.
- Focus, selection, district number, text, and truth badge redundantly encode
  the current gate.
- Reduced-motion preference removes drone, route, avatar, and door-wipe
  animation; a visible button offers the same choice.
- At narrow widths terminals become one column and cosmetic routes disappear.

The door wipe is a short presentation transition. It does not retain a replay
cursor, sandbox edits, candidate selection, or any other scientific state.

## Verification

```bash
cd game-ui-v2
npm run typecheck
npm test
npm run build
```

Deterministic visual review uses `hub.html` at `1440×1050`, forced reduced
motion, and a fixed virtual-time budget. A second capture focuses the synthetic
System Foundry door so the cross-mode truth grammar can be reviewed without
opening or combining its data contract.
