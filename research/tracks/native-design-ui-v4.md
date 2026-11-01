# Native visual system authoring v4

Date: 2026-11-01  
Track: game UI / native design surface  
Truth status: implementation and deterministic fixture-backed browser QA; no new native experiment was run

## Outcome

The NOCTILUCA Institution Foundry now projects the editable `SystemSpec` JSON into a visual graph authoring surface. A researcher can select, add, remove and rename mechanisms; edit family, implementation, parameters and schedule; add or remove typed ports; and add, remove or rewire connections with latency. Undo and redo operate on the whole `SystemSpec`. The advanced JSON editor remains synchronized and is still available for fields outside the visual surface.

The graph is the optimization design object, not a simulated world action. It does not claim to be a full science-management game. Spatial positions, the central rail and node styling are presentation-only.

## Execution and consent boundary

- Opening, viewing, editing, undoing, redoing and local structural checking do not call inference or create a durable job.
- The local TypeScript precheck mirrors important graph-reference, port, channel, schedule and required-input rules for immediate feedback. It is explicitly labelled as a local precheck and is not authoritative.
- `POST /native-api/validate` remains the authoritative validation boundary. Validation does not execute the system.
- Every system, loss, seed or year edit clears the validated request, unchecks the compute-consent checkbox and disables submission.
- Only the existing explicit `QUEUE NATIVE RUN` action can call `POST /native-api/jobs`. The durable worker and completed-evidence loading flow are unchanged.
- Browser QA intercepts only the session and validation endpoints with explicit fixtures. It fails all other native API paths and asserts that no job request occurred.

## Data ownership

`design-system` remains the canonical browser-side serialized value used by the existing request constructor. The visual authoring controller parses and updates that same textarea; it does not maintain a second execution contract. Unknown top-level and mechanism fields are preserved through edits. The Python `SystemSpec.from_dict` and `validate_system_spec` path remains authoritative at the API boundary.

Removing a mechanism also removes its schedules and attached connections. Removing a port removes attached connections. Renaming a mechanism updates schedule and connection references. These operations make referential changes explicit instead of leaving hidden dangling data.

## Validation evidence

- `npm run typecheck`
- `npm run build`
- `npm test`: 18 files, 128 tests
- `node scripts/verify-native-design-ui.mjs`: 15 pinned mechanisms and 18 wires loaded; node addition, rewire, undo/redo and consent invalidation verified; fixture validation returned; submit remained disabled; no `/jobs` request; no browser exceptions; no 390 px overflow
- `npm audit`: no known vulnerabilities at install time

Rendered evidence:

- `research/figures/native-design-ui-v4/native-visual-authoring-desktop.png`
- `research/figures/native-design-ui-v4/native-visual-authoring-mobile.png`
- `research/figures/native-design-ui-v4/browser-verification.json`

## Known limits

- The visual precheck intentionally does not replace Python validation and does not attempt to establish scientific quality, ethics or policy readiness.
- Artifact-type catalog editing, agent-type editing and global invariants remain advanced-JSON operations.
- Newly added mechanisms receive an explicit placeholder implementation string; a user must choose an implementation registered by the native runtime before execution can succeed.
- This slice authors a fresh candidate system. It does not migrate the loaded researcher society into the edited graph.
