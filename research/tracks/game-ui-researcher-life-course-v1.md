# Game UI: verified researcher identity and life course v1

Status: implemented and locally verified on
`track/game-ui-researcher-life-course-v1`, based on institutional-cutaway
integration commit `aa5057a`.

## Outcome

Researchers in the verified NOCTILUCA city are now identities with inspectable
life-course records rather than anonymous moving sprites. Selecting a city
researcher, an Evidence Quay worker, or the active researcher inside an
institution opens a dossier containing:

- a Year 0–1 canonical event timeline;
- authored-paper topics as the only research-direction evidence;
- paper, review, funding, research, reporting, and registration counts;
- a frame-backed resource trajectory and current balance;
- frame-backed active/inactive state and institution;
- artifact-mediated author/reviewer activity with peer IDs and event evidence;
- explicit observation limits and missingness.

Timeline and relationship evidence cards open the existing canonical event and
authoritative before/after-frame inspector. Relationship peer nodes switch to
that researcher's dossier. `D` opens the last selected dossier, while Escape or
the close control returns to the city.

## Evidence and inference boundary

`src/researcherLifeCourse.ts` first passes the same empirical,
commit-pinned, event/frame verification gate as Evidence Quay. It then reads
only canonical researchers, canonical events, and authoritative frame state.

Author direction is deliberately limited to topics attached to that author's
canonical `paper.submitted` event. A reviewed paper's topics are not attributed
to its reviewer. Resource points exist only where an event's post-event frame
has numeric `balance` and boolean `active`. The UI does not infer a departure:
an inactive frame is shown as `INACTIVE AT FRAME`, while the missingness rail
states that no explicit `researcher.exit` event type exists.

Artifact-mediated peer evidence is also narrow. A relationship exists only
when a canonical `review.completed` event names a reviewer and the matching
authoritative artifact state names its author. It is labeled as review evidence,
not inferred social collaboration.

The following remain `presentation_only` and are labeled above the dossier and
inside the relationship map:

- node position and relationship lines;
- avatar appearance and active/inactive expression;
- panel layout, visual grouping, and narrative styling.

Tests delete all choreography actions, visual flows, epistemic flows, interior
activities, and ambient records and confirm byte-equivalent dossier data.

## Missingness and time

The dossier follows the replay cursor. Events, topics, resource points, and
peer evidence appear only after their canonical timestamp. The authoritative
agent state comes from the latest frame at or before the cursor.

Every dossier names the run's observation limit. University researchers have
registration evidence in Year 0 and activity evidence in Year 1; this does not
license extrapolation into later years. A missing authored topic is displayed
as `NOT OBSERVED`, not as a claim that the researcher lacks a direction.
Absence in this finite simulation stream is explicitly not evidence of absence
outside the run.

## Accessibility and responsive behavior

- Researcher sprites and interior fact bars dispatch the same native dossier
  selection event.
- Timeline, evidence, and peer nodes are native buttons.
- Dossier state is exposed through a polite status region.
- `D` toggles the dossier; Escape closes it; all prior replay keys remain.
- Reduced motion is inherited and screenshots use a fixed cursor.
- At narrow widths the four dossier panels become one keyboard-scrollable
  column; the identity, truth boundary, current state, and missingness remain
  visible. A 720x900 Chromium review passed.

## Historical source and claim boundary

The source is the completed seed-521 engineering campaign, revision
`9a10029807d5`, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. This is not the running
metric-conditioned v1.1 result, a policy result, or evidence of scientific
optimality. The active v1.1 experiment worktree was not changed.

## Verification evidence

- Life-course projection tests: 6 passed.
- Complete Vitest suite: 75 passed.
- TypeScript typecheck and Vite production build: passed.
- Inactive-state dossier, two byte-identical runs:
  `253a7a2c85cf97e666fa0ada5f74105d4e71124ec91cdfeec166921863e0e5f2`.
- Active author dossier, two byte-identical runs:
  `8f799f72a92d0b460f2583f4d8c4e7c11fc3b3c5200b6ce5a060f0ba2f915824`.

Both captures use 1440x1050, verified campaign data, cursor 47,000 ms, direct
researcher selection, and reduced motion.
