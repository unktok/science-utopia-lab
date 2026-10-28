# Game UI: researcher life and institutional interiors v1

Status: implemented and locally verified on
`track/game-ui-researcher-life-v1`, based on epistemic-flow commit `cb21805`.

## Outcome

The verified NOCTILUCA seed-521 world now exposes the work inside its
institutions rather than showing only agents and inter-institutional routes.
Researchers walk to dedicated manuscript benches, review booths, application
terminals, decision consoles, and an award inbox. They visibly write, review,
apply, read decisions, and receive awards during the evidence-linked interval.

The deterministic layer contains:

- 11 derived workstations: two manuscript benches, two review booths, four
  shared application terminals, two decision consoles, and one award inbox;
- 20 derived interior activities: two writing, four review, ten application,
  two decision-reading, and two award-receipt records;
- 56 actor actions: 36 movement, two writing, four review, ten application,
  two reading, and two receipt actions.

Application costs are grouped by canonical actor for legibility. Each grouped
activity and action retains all canonical `funding_application_cost` source
IDs; no cost, actor, or transition is reconstructed in the browser.

## Projection-only and provenance boundary

Python remains authoritative for interpreting the commit-pinned campaign.
Workstations, activities, paths, labels, and timing are deterministic
presentation projections. Every non-cosmetic record has `truth_status:
derived` and cites canonical event IDs. The browser only validates and renders
those declared records plus authoritative projection frames.

Python and TypeScript fail closed when a workstation is unknown, geometry is
not integer-aligned, a source event is missing, an event type differs, or the
activity semantics disagree with canonical actor/category/event data. A
verified campaign must contain both workstations and interior activities.
Tamper tests cover both semantic substitution and missing evidence.

The two ambient interior effects are deliberately separate:

- console flicker;
- break-room vapor.

Both use `truth_status: ambient`, have no canonical source IDs, and are
controlled by the independent `COSMETIC` toggle. They are not evidence that a
simulated researcher used a console or took a break. The live `INTERIORS`
status, selection inspector, truth legend, and semantic keyboard mirror keep
this distinction visible.

## Pixel-art extension

The repository-owned asset pack is now `noctiluca-production-v0.5`. Five new
32x24 station sprites use only fixed-palette, integer-aligned SVG rectangles
with `crispEdges`: manuscript, review, application, decision, and award. Their
silhouettes and instruments differ so the work type is not communicated by
colour alone. Asset tests continue to reject unregistered colours, curves,
transforms, filters, external assets, and dimension drift.

## Historical source and claim boundary

The default portable bundle is still the completed engineering-demo campaign
revision `9a10029807d5`, seed 521, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. It is not the running
metric-conditioned v1.1 result, a policy result, or evidence of scientific
optimality. The frozen experiment worktree was read only for the already
commit-pinned historical artifacts and was not modified.

The 1,024,724-byte portable bundle has SHA-256
`2097889201a675594b3ea13567c17017dcbc366a0526e982afce6829af777422`.
Its canonical hashes remain unchanged:

- Python stream: `ba0bb641d99888246b349bcce153340beff7ab21a5a0c1ed0052c7f31a6ba540`;
- browser stream: `c37b5e4d23fb2332641b545054bd2fda97836f1b9ecb29d9c252dd94a03fdc39`.

## Verification evidence

- Python replay/adapter suite: 28 passed.
- Vitest UI, asset, semantic, and screenshot suite: 32 passed.
- TypeScript and Vite production build: passed.
- Actual campaign re-export: byte-identical to the committed portable bundle.
- Writing interior, two byte-identical captures:
  `bbcb21a6f4e9f18216d6bf47ce1dfdd0a1e51e9cfbb318b41fa202b48623a584`.
- Review interior with camera follow, two byte-identical captures:
  `1da1e23bb561fcf0e270665e3bf8bb450067c54d997adc3a8c380229e5bf91a7`.
- Application interior with camera follow, two byte-identical captures:
  `0a0393ac54e5ad2b0933a91ad8a6f83b5ce86e46d586e098b37da39ec2069937`.

All captures use a 1440x1050 viewport and reduced motion. Each keeps the
derived record, canonical source event, and source disclosure visible in the
same frame.
