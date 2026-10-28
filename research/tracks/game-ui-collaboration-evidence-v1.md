# Game UI: verified collaboration / evidence navigation v1

Status: implemented and locally verified on
`track/game-ui-collaboration-evidence-v1`, based on researcher-dossier
integration commit `0cf6c39`.

## Outcome

The verified NOCTILUCA campaign can now be navigated as a typed evidence graph
between researchers, artifacts, institutions and canonical funding-activity
events. The graph is reachable from the city, the active institutional
interior fact bar and every researcher dossier. It drills back into dossiers,
switches graph focus for artifacts/institutions, and opens the exact source
event from an edge or the canonical lineage strip.

The seed-521 fixture contains 12 researcher nodes, two artifact nodes, two
event-backed institution nodes and 28 funding-activity event nodes. It has ten
affiliation, two authorship, four reviewer and 28 funding-activity edges. It
has no observed coauthor, funder or citation edges.

## Evidence contract

`src/collaborationGraph.ts` passes the same empirical, commit-pinned
event/frame verification gate as Evidence Quay before building anything. It
then consumes only canonical events/researcher identities and authoritative
artifact identities:

- `agent.registered` with an explicit institution creates affiliation;
- `paper.submitted` creates authorship, and coauthor only when the same event
  explicitly names more than one actor;
- `review.completed` creates reviewer only for explicitly named actors;
- funding application cost and grant income create `funding_activity` event
  nodes, not funder identities;
- funder requires an explicit canonical `funder_id` and a known node;
- citation requires a canonical `citation.created` event naming two artifacts.

The edge list carries its source event ID and event kind. Cursor projection
removes future events, edges and disconnected nodes. Deleting every
choreography and ambient record leaves graph evidence byte-equivalent.

## Missingness and type safety

Coauthor, reviewer, funder and citation observation cards are visibly labelled
`RUN` and summarize the loaded verified run as `observed`,
`not_observed` or `identity_missing` for the loaded finite run. In particular,
the existing funding changes do not identify a source institution, so the UI
shows funding activity while keeping `FUNDER 0 · IDENTITY MISSING` visible.
Anonymous/missing review actors produce no reviewer edge. Institutions,
topics, spatial proximity and story context are never used to fill identities.

The adapter explicitly types force layout, node placement, edge routes, edge
animation, colour and narrative labels as `presentation_only`. That list also
appears in the graph boundary and canvas. These choices cannot create nodes,
edges, observation counts or event lineage.

## Interaction, accessibility and responsive behavior

- `G` toggles the graph and Escape closes it.
- Edge filters, nodes, evidence records and lineage marks are native controls.
- Each edge type has a text label; colour is not the only distinction.
- The graph focus, truth boundary, missingness and source-event controls remain
  available in reduced motion.
- `prefers-reduced-motion` disables packet animation through the global motion
  contract.
- At widths below 900px the graph becomes a fixed, scrollable full-screen
  terminal with stacked filters, canvas and evidence list. A 720x900 Chromium
  review passed.

## Historical source and claim boundary

The source is the completed seed-521 engineering campaign, revision
`9a10029807d5`, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. This is not the running
metric-conditioned v1.1 result, a policy result, or evidence of scientific
optimality. Synthetic replays fail closed. The active v1.1 experiment worktree
was not changed.

## Verification evidence

- Collaboration graph contract tests: 6 passed.
- Complete Vitest suite: 83 passed.
- TypeScript typecheck and Vite production build: passed.
- Artifact authorship/reviewer view, two byte-identical captures:
  `587064a7f46b8207b50ab7b3ac3bc5ef39010105c15a9132af24e4dd1f3d9485`.
- Researcher funding-activity view, two byte-identical captures:
  `00cb4f7ab85131b305880bdd63752ea94d001389150e6d5a2b6e6f47aeebf6c5`.

Both reviewed captures use 1440x1050, verified campaign data, cursor 47,000
ms and reduced motion.
