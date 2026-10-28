# Deterministic visual QA

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

Publication is implemented and automatically checked but is not one of the
three institutions placed in this replay fixture. Directional walking, longer
cycles, external art review, and external accessibility review remain later
gates.
