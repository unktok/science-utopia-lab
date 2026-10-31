# Native System Foundry UI v1

Nov1 update: the new DESIGN WORKBENCH now edits complete SystemSpec/LossSpec
JSON and submits an explicitly consented fresh native branch through a local
durable queue; actual completed evidence returns to this same UI. This closes
the job round-trip gap described below, not in-place society migration or full
gameplay. [Result](../results/native-feedback-breadth-v2.md) and
[runbook](../components/native-feedback-and-interactive-design-v2.md).

2026-10-31. Local-only extension of the existing NOCTILUCA pixel/cyberpunk UI.
The user accepts a game-like institutional design UI as the first deliverable;
a complete playable science-management game remains a later target.

`game-ui-v2/native.html` loads hash-bound ORIGINAL native-world design evidence,
not the older numeric miniature. The default snapshot is the live hard/soft
institution probe (initial native loss0, fitted native loss-3). Its exact
source/IR, ports, actual wiring and schedules, selected-year real researchers/
resources, native execution receipts and loss lineage are inspectable.
The UI explicitly distinguishes conditional soft fitting from actual native
loss and fixes LLM-weight/full-world-autograd/live-intervention claim flags.

Buildings, positions and sprite poses are schematic presentation, not simulated
locations. Clicking a mechanism or NEXT EXECUTION selects actual recorded
mechanism events; it does not create scientific events or run new institutions.
Failed candidates retain null loss and lack fabricated researcher activity.
Other native campaign snapshots can be loaded from a file.

Exporter: `scripts/export_native_design_lab.py` validates campaign lineage,
kernel/checkpoint identity and completed-year frames, then emits a raw-byte-
hashed envelope. Exact canonical SystemSpec bytes have their own independently
checked fingerprints in the browser. It exports native mechanism events and
author snapshots, not raw model-response caches. This is checksum integrity,
not a signature or an attestation of scientific realism.

Verification: frontend113 tests pass; production TypeScript/Vite build passes
(the pre-existing large Phaser chunk warning remains). Real local Chrome checks
both candidate selection, five real authors, source inspection, NEXT EXECUTION,
desktop and390px mobile layout. No browser exceptions, failed requests or
horizontal overflow. Sprite sheets are cropped to a single proper24x32 frame
rather than displaying a miniature row of all six frames. No external image
service, new dependency, public hosting or deployment was used.

Local preview: `cd game-ui-v2 && npm run dev -- --host 127.0.0.1 --port 4189`.
Reproduce browser QA with a task-owned local Chrome CDP port9341 and
`node scripts/verify-native.mjs ../outputs/native-design-ui`.
Screenshots/browser report remain under `outputs/native-design-ui/`.

Remaining: edit/compile a player design, submit it to an isolated native branch,
show genuine pending/completed observations; arbitrary new role/protocol
visualization and deeper game feedback. Current controls are honest read-only
evidence inspection, not that installation workflow.

Language policy (2026-10-31): game interfaces are English; research notes and
explanatory material may remain Japanese. Native and numeric foundry headings,
controls, accessible labels, empty states and errors now use English. Scientific
evidence and generated source remain verbatim. The LOAD RUN input stays keyboard
accessible behind an English label, without OS-localized file-input chrome.
All eight game HTML entries declare English. Frontend118 tests and production
build pass; real Chrome verifies English default copy, both candidates/objectives,
and desktop/390px mobile layouts without overflow or runtime errors. Updated
screenshots and reports: `outputs/native-design-ui-en/` (local, untracked).

## Control-room redesign (2026-10-31)

The generic landing-page headline was not consistent with the game's existing
creative direction. It has been replaced with an Institution Foundry design
deck: original crisp vector/pixel control-room art, research-city windows,
network workstation, server racks, an engineer and a secondary terminal. This
is a standalone presentation scene, not additional simulated world content.
The scene's artist/provenance note distinguishes it from the fixed runtime
sprite atlas; there are no third-party or remotely loaded image resources.

The adjacent record-inspection console has explicit READ ONLY status, an
evidence-backed mechanism/connection/year summary, selected mechanism telemetry,
and a link into the real graph. The graph/source/actor/loss evidence contract
is unchanged. Fixed weights, native records, no live installation and schematic
spatial layout remain visible. All UI copy stays English.

Verification:120 frontend tests, production build (existing Phaser warning),
real Chrome desktop/390px mobile, art-load check, year/count/selection telemetry,
source and execution selection, English copy and no overflow/runtime errors.
Numeric foundry browser regression also passes. Full/deck/mobile captures and
QA report: `outputs/native-foundry-control-room/`. The paper contains the actual
deck capture plus a source/image hash manifest, not a mockup. It remains an
inspection interface, not a completed playable management game.
