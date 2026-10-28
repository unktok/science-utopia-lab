# Game UI: science-system design console and sandbox v1

Status: implemented and locally verified on
`track/game-ui-system-sandbox-v1`, based on researcher-life commit `6ce3bde`.

## Outcome

NOCTILUCA now has an independent system-design page where the whole science
system is the object being edited. The console presents five ordinary
`MechanismSpec` nodes:

- evaluation;
- publication;
- funding;
- government, represented by the `governance` family;
- communication.

Each node can be enabled or removed and has two implementation identifiers.
Six typed edges can be enabled or removed and assigned latency zero, one, or
two. The graph, channel router, complete canonical `SystemSpec` JSON,
fingerprint, and validation report update together. Reset and a deliberately
invalid disconnected-publication preset are keyboard accessible (`R` and `B`)
in addition to native buttons, checkboxes, and selects.

This is structure exploration only. The UI never executes the mechanism graph,
scores a system, optimizes it, or displays an outcome.

## Authority and claim boundary

`utopia.system.sandbox.build_system_sandbox_bundle()` constructs the starting
graph with the repository's real `SystemSpec` classes and validates it with
`validate_system_spec`. The exporter writes a portable contract containing:

- the complete base spec;
- node and edge editing catalogs;
- a valid fixture and a publication-input-disconnected fixture;
- Python-computed fingerprints and validation reports;
- a SHA-256 over the complete contract.

The browser parser accepts only
`truth_status: synthetic` and
`source_kind: synthetic_system_design_sandbox`. Any attempt to claim canonical,
verified, or empirical provenance fails closed. It verifies the contract hash,
recomputes both Python fixture fingerprints, and requires exact parity with the
valid and invalid Python validation reports before enabling the editor.

The browser validator mirrors the relevant SystemSpec v1 structural contract:
known typed endpoints and ports, channel and artifact compatibility, required
inputs, schedules, non-negative integer latency, and unique connections. It is
not a new scientific evaluator. The UI states this distinction in the header,
disclosure strip, validation card, and footer.

The verified seed-521 replay remains on `index.html` with its existing
campaign adapter. The sandbox is a separate entry point and loads only
`system-sandbox.contract.json`; it does not import replay events, projection
frames, metrics, results, or v1.1 artifacts. Its link to the verified replay is
navigation, not data composition.

## Starting graph

The valid base graph has the following typed loop:

```text
government --constraint--> evaluation --decision--> publication
     |                                               |
     +--constraint--> funding --resource, L1--------+--> evaluation
                                                     |
publication --artifact, L1--> communication --signal, L1--> government
```

The graph has five scheduled mechanisms and six connections. Its canonical
fingerprint is
`9a6262161548ff0a80897f29b62fad2988df02360c2b4812a1e24bf4f87c5314`.
Fingerprint identity covers node presence, implementation choice, edge
presence, channel contract, latency, schedule, metadata, and the rest of the
complete `SystemSpec`.

Disabling the evaluation-decision edge leaves publication's required decision
input unconnected. Python and the browser both report
`unconnected_required_input`; this is a technical invalidity, not an adverse
scientific result.

## Pixel-art and accessibility

Asset pack `noctiluca-production-v0.6` adds five original 48x40 fixed-palette
glyphs for evaluation, publication, funding, government, and communication.
They use integer-aligned `rect` primitives and `crispEdges`; no external or
generated asset is used. They are explicitly synthetic structure icons, not
campaign institutions.

The map supplements colour with labels, silhouettes, edge text, typed channel
names, latency labels, enabled state, and validation outlines. Every edit is
also available in the semantic channel-router form. Native controls, a skip
link, live status regions, visible focus, reduced motion, responsive stacking,
and non-colour error text cover keyboard and assistive use.

## Deterministic artifacts and verification

The 23,945-byte portable contract has file SHA-256
`7944314bccbf3531e50f7d4d190f704460ad83aac67e9b436703c35e24bfdcc5`
and internal canonical contract hash
`ded9a61d2df8b0f131a8238e1440987a342045aa9e7877f00f0c4fdbd2932be3`.

- Python SystemSpec and sandbox suite: 21 passed.
- Vitest UI, contract, asset, replay, and screenshot suite: 39 passed.
- TypeScript and Vite three-entry production build: passed.
- Python contract re-export: byte-identical to the committed portable bundle.
- Valid sandbox capture, two byte-identical runs:
  `835da7a83355eff5b338fc262d6b3905408d7c4dfb767a47c7b049f70d9604f3`.
- Invalid publication-input capture, two byte-identical runs:
  `d0007a200d82ce38633dcb1bc7e9c21c87e1a51ca96aeb42768b47dce42bc047`.

Both captures use a 1440x1050 viewport and reduced motion. The frozen v1.1
worktree was not modified. No campaign result, held-out metric, optimization
loss, or promotion policy was introduced or consumed.
