# Scientific-system concept figure: visual refinement v2

2026-11-01. User feedback: retain the overall idea, fix route seams and box/text
spacing, graphically explain the four design freedoms in the same figure, and
remove the game interface as a standalone scientific component.

## Changes

- Parameters: the track/rule remains while a setting moves.
- Algorithms/source: replace executable function f with g, not just a value.
- Mechanisms/protocols: add an institution and new message-carrying connections.
- Wiring/order: preserve the colored nodes but alter their routes and order.

The four cards feed the SAME scientific system in parallel. There is no arrow
sequence implying a mandatory parameter -> code -> mechanism -> wiring pipeline.
Institutions and responsive researcher activity now share one enclosing world.
Objective choice, system design and search method remain distinct. Independent
reporting remains separate from the declared optimization loss. The game remains
a whole-system presentation/interaction track; omitting its box does not remove
that project goal or change its implementation.

## Geometry and verification

Each connector shaft is one continuous vector Path, with zero implicit endpoint
shrinking. Round joins replace the old separately drawn polyline/final-arrow
segments, whose default shrink caused visible gaps. Boxes have exact declared
geometry (pad=0), and external arrows use a consistent4-point optical gap.
Internal node connectors have1.5-point gaps. Circular nodes and margins use
physical points, so the x/y aspect ratio cannot flatten the circular glyphs.

Automated checks cover canvas clipping, pairwise text overlap, at least4 points
of panel text padding (2 for tiny mechanism labels), route/text intersections,
single continuous connector paths and deterministic PDF/SVG/PNG bytes. These
augment, not replace, PNG and final manuscript-page inspection. The generator
refreshes the manifest with hashes of its source and all three output assets.

Scope: figure generator/assets, Figure1 caption, derived shareable PDFs, tests
and explanatory notes only. No simulation, objective, metric, optimizer, active
experiment worktree, saved native evidence or game-UI implementation is changed.
The image is conceptual, not empirical evidence or a capability-completion map.

Verification:54 report tests pass in6.35s. The rebuilt paper remains17 pages;
all pages were re-rendered and Figure1 was inspected enlarged. TeX reports no
undefined references or overfull boxes. Both shareable PDFs are refreshed.
