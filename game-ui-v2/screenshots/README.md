# Deterministic visual QA

## Science-system design sandbox

These 1440x1050 captures show the isolated `SYNTHETIC SANDBOX`, not a replay
or experimental result. The first is the Python-validated five-mechanism base
`SystemSpec`. The second disables the evaluation-to-publication decision edge
and exposes the resulting `unconnected_required_input` technical error.

| Capture | SHA-256 |
|---|---|
| `noctiluca-system-sandbox-valid.png` | `835da7a83355eff5b338fc262d6b3905408d7c4dfb767a47c7b049f70d9604f3` |
| `noctiluca-system-sandbox-invalid-publication.png` | `d0007a200d82ce38633dcb1bc7e9c21c87e1a51ca96aeb42768b47dce42bc047` |

Both were repeated from separate empty Chrome profiles and were byte-identical.
The valid and invalid captures use reduced motion and keep the claim boundary,
SystemSpec fingerprint, graph validity, node implementations, and edge
latencies visible together.

## Researcher life and institutional interiors

These 1440x1050 reduced-motion captures are driven by the verified completed
seed-521 campaign. They open derived interior activity records alongside their
canonical sources; the review and application views enable camera follow to
make their institutional workspaces legible.

| Capture | SHA-256 |
|---|---|
| `noctiluca-life-writing-seed521-cursor-6200.png` | `bbcb21a6f4e9f18216d6bf47ce1dfdd0a1e51e9cfbb318b41fa202b48623a584` |
| `noctiluca-life-review-seed521-cursor-20200.png` | `1da1e23bb561fcf0e270665e3bf8bb450067c54d997adc3a8c380229e5bf91a7` |
| `noctiluca-life-application-seed521-cursor-36500.png` | `0a0393ac54e5ad2b0933a91ad8a6f83b5ce86e46d586e098b37da39ec2069937` |

Each capture was repeated from a separate empty Chrome profile and was
byte-identical. The visible `INTERIORS` layer is evidence-linked and derived.
The independently switchable `COSMETIC` layer contains only records marked
`ambient`, with no canonical source IDs.

## Verified completed campaign capture

`noctiluca-completed-campaign-seed521-cursor-9000.png` is the first capture
driven by an actual completed, commit-pinned campaign run rather than the
synthetic renderer contract. It shows twelve registered agents, three derived
institution nodes, two papers, and simultaneous paper/review flows from the
completed seed-521 run. Its SHA-256 is
`eb984c5aaadc69aeddb5b9b5d07b840e85f7649c1a19bef0fba7bf7e518aa923`.

The 1440x1050 reduced-motion capture at cursor 9,000 ms was generated twice
with separate empty Chrome profiles and once directly to the tracked path; all
three PNGs were byte-identical. The visible disclosure identifies the source as
the completed 2026-10-27 engineering demo and explicitly excludes the running
metric-conditioned v1.1 study and policy/optimality claims.

Capture URL: `/?replay=campaign&motion=reduced&cursor=9000`.

## v4 spatial activity captures

The v4 captures use a 1440x1050 viewport, cursor-fixed reduced motion, the
four-researcher synthetic replay contract, and production asset pack v0.3.

| Capture | SHA-256 |
|---|---|
| `noctiluca-v4-review-network-cursor-20000.png` | `38a8766980a149cfcec33244a6133e3444684c8ab5314a4ac84d7760cfea1183` |
| `noctiluca-v4-publication-funding-cursor-26000.png` | `4516ddd36a8da5a295978ccdec13eb8c0417068abf45323de73f532dd4b585b1` |
| `noctiluca-v4-publication-evidence-cursor-26000.png` | `8d65b81b37cabf8bb7597d35052fb34bab45cd3b2001f9361a77e2d9a7bbb58b` |

The publication/funding capture was produced twice with separate Chromium
profiles and compared byte-for-byte. It shows Iren operating the Publication
Spine while Sol works in the Civic Ledger. The evidence capture opens Iren's
derived publication action and its canonical `paper.decided` source. The
review-network capture shows Mino in the review chamber while the submitted
paper moves spatially between the lab and exchange.

All visible work effects are selected from active `choreography.actions`; the
renderer does not infer work from occupation, balance, or paper outcome.

Capture recipe after `npm run dev -- --host 127.0.0.1 --port 4173`:

```sh
CHROME=/path/to/google-chrome
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1440,1050 \
  --virtual-time-budget=5000 --run-all-compositor-stages-before-draw \
  --user-data-dir=/path/to/a/new/empty/profile \
  --screenshot=screenshots/noctiluca-v4-publication-funding-cursor-26000.png \
  'http://127.0.0.1:4173/?cursor=26000&motion=reduced'
```

## Intervention branch comparison

The side-by-side captures use a 1440x1000 viewport and synchronized cursor
43,000. Both 480x270 worlds are bound to separate canonical streams with an
identical six-event prefix. The inspector capture opens Future B's canonical
`policy.changed` intervention payload.

| Capture | SHA-256 |
|---|---|
| `noctiluca-branch-compare-cursor-43000.png` | `1998000843e58adb04b3be4d2bcfaf0c42dfaee9e89fd29925d9b03fa117a70a` |
| `noctiluca-branch-compare-intervention-evidence.png` | `7072d271255ae88fb4cf7bb14544badcc1c9f3d56c5cd2a0353a25f293eca6ce` |

The comparison capture was repeated with the same Chromium build and was
byte-identical. Visual review confirmed distinct branch framing, the common
origin and three-hash verification state, synchronized cursor, authoritative
outcome strips, and canonical intervention drill-down.

## v3 living-arcology captures

The v3 captures use a 1440x1050 viewport and reduced motion. The world canvas
remains 480x270 and renders at integer scale. The browser loaded
`noctiluca-production-v0.2`; no concept PNG is part of the runtime asset pack.

| Capture | SHA-256 |
|---|---|
| `noctiluca-v3-paper-action-cursor-14000.png` | `685630319873eb71efe5597911f7da63e2d803fb71e1017c8a29a9f3977f611f` |
| `noctiluca-v3-action-evidence-cursor-14000.png` | `3ce9261480c264f497d4f36c91d500985966d1e8fb4eec43db3aa83871b5543c` |
| `noctiluca-v3-funding-cursor-28000.png` | `920b110d2c067e2f390cf0b4a95887016a65b8efc75ec9cadffb2a986e2f1aa3` |
| `noctiluca-v3-policy-cursor-43000.png` | `b7c386bbe020a6b77c05d191c4723c41c3b960d190575484f13124cb7c75dd96` |

The paper/action capture was repeated in the same headless Chromium build and
was byte-identical. It shows Aya writing and Mino reviewing while the paper
packet crosses the exchange. The evidence capture opens Aya's derived action
and its canonical `paper.submitted` source. The later captures exercise funding
allocation and policy transmission with role-specific poses and packet trains.

## v2 baseline

The earlier two captures use replay cursor `28000` and production asset pack
v0.1. They remain checked in as a before/after visual baseline.

| Capture | SHA-256 |
|---|---|
| `noctiluca-vertical-slice-cursor-28000.png` | `d9480c1187ba3f8f39e22026b572ddaac6cba4bb6bcb553b31f99cf9dab9ff4d` |
| `noctiluca-evidence-funding-cursor-28000.png` | `5f8ba166a0395497592605d99edd35bb442c0172db700c9d8699b5dd15b06af7` |

Capture recipe:

```sh
CHROME=/path/to/chrome-headless-shell
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1440,1050 \
  --virtual-time-budget=4000 \
  --screenshot=screenshots/noctiluca-v3-paper-action-cursor-14000.png \
  'http://127.0.0.1:4173/?cursor=14000&motion=reduced'
```

## Review record

- Lab, peer-review exchange, and funding authority remain recognizable from
  silhouette at the 96x80 logical grid; their cutaways show distinct work.
- The laboratory reads as a patched instrument stack with sample tank,
  benches, pipes, and greenhouse activity.
- The exchange reads as mirrored anonymous review booths around a routing eye,
  with visible queue and decision signals.
- The authority reads as a stepped vault with application intake, ledger, and
  outward allocation ports.
- Three researchers remain distinct at 24x32 by posture and equipment, not
  merely colour.
- Six 8x8 packets use different shapes. Line pattern and the evidence inspector
  redundantly communicate truth status.
- Selecting the funding flow opens its `derived` record and links to the
  canonical `resource.changed` evidence event.
- No missing-asset state or application error appeared during either capture.

v3 additionally passed these visual checks:

- idle, walk, and work poses have distinct silhouettes and equipment;
- action labels state `DERIVED` and active actors drill into canonical evidence;
- paper, review, funding, and policy routes remain distinguishable by packet,
  cadence, echo count, endpoint mark, label, and colour;
- environment rain and courier are visibly subordinate and marked ambient;
- the cursor-14,000 capture is byte-deterministic.

v4 additionally passed these visual checks:

- four institution silhouettes remain legible at the 480x270 logical canvas;
- the submission, review-return, publication, citation, funding, and policy
  routes occupy distinct spatial arcs;
- researcher workstations change only while an evidence-linked action is
  active and freeze to a representative frame under reduced motion;
- the editor sheet and Publication Spine use the frozen palette, integer
  rectangles, and crisp-edge production contract;
- the cursor-26,000 capture is byte-deterministic.

Directional walking, longer cycles, external art review, and external
accessibility review remain later gates.
