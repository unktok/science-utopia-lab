# Native observed preference regions

These four files are byte-preserved outputs of two actual read-only exports at
26497eef3589e13ef95fdfee167b946e39455012. They describe the normally closed
61a1753 T/U development, not new inference or a newly optimized objective.

| File | SHA256 |
| --- | --- |
| summary.json | 1438fd789bc54abfb4d883799ab6a2b67cd94443fce2ba3013215a00e06bee9a |
| preference-regions.png | 3b349046a238507cfea83c2b6b5e6667d1478f3e19dea2e94fa56f9cd18a799c |
| preference-regions.svg | 177adab3a114fba2d146218a0d66386ace131e41d84b4d3e7892a3f323b20b07 |
| manifest.json | 8b272220379ce8732ff92b0c1dc696bf0875433aca3143a2de635005b470f269 |

The sealed summary content hash is
676bedabbb686c07d841555711fda9b955aa98118780e03536dd14b520ae8bc4.
Its three score lines list all11 completed physical identities. Both failed
attempts remain outside the envelope; no partial count or score is imputed.
The manifest binds the original full report file/content hashes, reader source
and output hashes. Its input report is retained under
research/data/native-objective-instrument-loop-v1/report.json.

In a clean checkout of that reader source with the existing environment:

```sh
PYTHONHASHSEED=42 HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES= \
  .venv/bin/python -m scripts.reports.native_preference_regions_v1 \
  --report research/data/native-objective-instrument-loop-v1/report.json \
  --output outputs/native-preference-regions-fresh
```

Use an unused output path. A second export must use a different fresh path and
the same literal input/source. No original raw, active source or historical
receipt needs editing. This rebuilds the conditional numerical figure, not
the underlying native simulations, the observer or scientific truth.
