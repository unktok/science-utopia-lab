# Native design figures, 2026-10-31

`native-design-evidence.pdf` / `.png` are actual recorded development evidence,
not synthetic previews. Regenerate from the repository root without inference:

```sh
.venv/bin/python -m scripts.figures.native_design_evidence
```

The generator validates the checksum-bound native viewer payload against the
independently audited compact result, exact SystemSpec fingerprints, native
count/loss agreement, trace identity and installed fitted parameters. The left
panel is conditional soft fitting on frozen observations; the right panel is
actual fresh native hard execution. They must not be joined into a common loss
trajectory or compared with separate source/graph probes as a method contest.
One development seed and a gameable count target do not establish better science.
Input and output SHA-256 values are in `native-design-evidence.manifest.json`.

`native-foundry.png` is an actual 1440x600 browser capture of the native page's
control-room deck and controls. Reproduce with Vite on127.0.0.1:4189 and an
isolated local Chrome CDP session on9341:

```sh
cd game-ui-v2
node scripts/verify-native.mjs ../outputs/native-foundry-control-room
```

The generated `native-foundry-deck.png` is the paper image. Its initial source
file hashes, viewport/clip and image hash are retained in
`native-foundry.manifest.json`. Control-room geometry and characters are
schematic art, not inferred native agent positions. All controls are read only;
this image does not establish playable intervention or full-world autograd.
