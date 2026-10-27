# Deterministic visual QA

The two checked-in captures use a 1440x1050 viewport, replay cursor `28000`,
and reduced motion. The world canvas remains 480x270 and renders at integer
scale. The browser loaded `noctiluca-production-v0.1`; no concept PNG is part
of the runtime asset pack.

| Capture | SHA-256 |
|---|---|
| `noctiluca-vertical-slice-cursor-28000.png` | `d9480c1187ba3f8f39e22026b572ddaac6cba4bb6bcb553b31f99cf9dab9ff4d` |
| `noctiluca-evidence-funding-cursor-28000.png` | `5f8ba166a0395497592605d99edd35bb442c0172db700c9d8699b5dd15b06af7` |

The world capture was repeated in the same headless Chromium build and was
byte-identical. Capture recipe:

```sh
CHROME=/path/to/chrome-headless-shell
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1440,1050 \
  --virtual-time-budget=4000 \
  --screenshot=screenshots/noctiluca-vertical-slice-cursor-28000.png \
  'http://127.0.0.1:4173/?cursor=28000&motion=reduced'
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

This is the first static production-grid slice, not the final animation pass.
Publication is implemented and automatically checked but is not one of the
three institutions placed in this replay fixture. Full state animation,
external art review, and external accessibility review remain later gates.
