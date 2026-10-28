# Game UI: verified completed-campaign adapter v1

Status: implemented and locally verified on
`track/game-ui-real-campaign-adapter`.

## Outcome

NOCTILUCA now defaults to a portable replay derived from an actual completed
campaign run. The browser does not load or interpret a simulator checkpoint.
The Python adapter verifies the source, converts it to canonical events,
replays every prefix through the authoritative projector, and emits the
browser-safe replay-view v2 bundle.

The checked bundle contains 71 canonical events, 72 authoritative frames, 12
registered agents, three normalized institution nodes, two papers, eight
evidence-linked flows, and eight evidence-linked actions. It is 891 KB and has
SHA-256
`4921900817964447dfc239e850e2ccca585285f825e6c94583d848d791ab5e21`.

## Historical source and claim boundary

The source is the completed `first-closed-loop-engineering` campaign, revision
`9a10029807d5`, at source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. The selected run is suggestion
`s5aad19dd3da73bc8`, seed 521:

`opt-first-closed-loop-engineering-9a10029807d5-smoke-optimization-d818522bc230e-s521`

This campaign completed on 2026-10-27. It is an engineering demonstration,
not the currently running metric-conditioned v1.1 study, not a policy result,
and not evidence of scientific optimality. The UI repeats that boundary in a
visible provenance strip.

The source declaration is
`research/artifacts/game-ui-completed-campaign-adapter-v1.json`. It pins the
campaign result, native run manifest, integrity report, checkpoint, resource
ledger, and resource balance ledger by SHA-256. The ignored raw files remain in
the historical local campaign directory and are not copied into the web app.

## Fail-closed boundary

Export stops before conversion if any of these checks fails:

1. source declaration or selected run is not terminal `complete`;
2. campaign id/revision/commit/completion timestamp disagrees with the tracked
   result;
3. suggestion, run id, and seed are not bound in that completed result;
4. a source path escapes its declared root, is absent, or has a hash mismatch;
5. the native manifest is incomplete, dirty, or has a different commit/run;
6. the native integrity report is empty, failed, or records failures;
7. a canonical event identity or stream hash changes;
8. any stored projection frame differs from Python `replay(events[:cursor])`;
9. the portable bundle contains a top-level raw simulator-state structure.

Scientific activity is visualized only from canonical `paper.submitted`,
`review.completed`, and `resource.changed(category=grant_income)` events.
Every placement, flow, and action cites its source event IDs. No citation or
policy flow is invented when the selected run has no such canonical event.

## Hashes in two runtimes

The bundle retains the authoritative Python canonical stream hash:

`ba0bb641d99888246b349bcce153340beff7ab21a5a0c1ed0052c7f31a6ba540`

JSON parsing in JavaScript erases the lexical distinction between `13.0` and
`13`. Therefore the adapter separately records a browser-normalized web stream
hash. Every JSON number is represented by its browser-visible IEEE-754 bits,
and the distinct algorithm id avoids relabeling it as the Python hash:

`c37b5e4d23fb2332641b545054bd2fda97836f1b9ecb29d9c252dd94a03fdc39`

The UI recomputes the web hash before constructing the Phaser scene and fails
closed on a mismatch. Replay selection is an alias allowlist: `campaign`
(default) or `synthetic`; arbitrary URLs are rejected.

## Reproduction

From the repository root, with `CAMPAIGN_ROOT` set to the completed revision
directory:

```sh
.venv/bin/python scripts/export_game_replay.py \
  --campaign-source-manifest research/artifacts/game-ui-completed-campaign-adapter-v1.json \
  --campaign-root "$CAMPAIGN_ROOT" \
  --view-version 2 \
  --output game-ui-v2/public/data/completed-campaign.replay.json
```

The command is read-only with respect to `CAMPAIGN_ROOT`. This work did not
change the frozen first-closed-loop or metric-conditioned v1.1 worktrees.

## Verification evidence

- Python replay/adapter suite: 23 passed.
- Vitest UI suite: 21 passed.
- TypeScript and Vite production build: passed.
- deterministic 1440x1050 screenshot: three byte-identical captures;
  SHA-256
  `eb984c5aaadc69aeddb5b9b5d07b840e85f7649c1a19bef0fba7bf7e518aa923`.

The current canonical entity catalog exposes every `agent.registered` actor in
the researcher-facing collection, including the two funding-agency actors.
Their `agent_type` remains in canonical payloads, but a future schema should
add a first-class agency entity group instead of relying on presentation
placement. No role was rewritten in this slice.
