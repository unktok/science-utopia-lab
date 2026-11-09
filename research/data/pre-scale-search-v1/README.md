# Closed T/E native search: retained data

This is the complete compact projection of the finite four-year pilot at
source `62388a74d071a3a4fdc8cc309c2807422f96223f`, plan
`db2df5c5e54a68c8201b6b8c460cffa66770ee37da4f7b0d1089c7f5fc7702cb`.
The two full original-source audits match byte-for-byte, content
`85d4698ff09dd6cfbfe8b83790f8ae28dbf27072de9853184adc1db4334b92d1`.
They verify 1,859 raw files and 49 physical worlds, including five partial
runtime failures. There are no replacement slots or repaired candidates.

`report.json` retains all sixteen submitted systems and their executable source,
six references, eight fixed selections including ties, 49 physical measurements
and 36 logical evaluation rows sharing 27 jobs. Each selected policy has three
unused seeds. `world-components.csv` retains A/Q/R statuses and cross-scores,
including unknown values for failures. `costs.json` separates scientist,
designer, readiness and load records. Cached input and nested timings overlap;
unknown counts are not zero. `mechanism-changes.json` projects literal changes
from the common initial, not semantic novelty or guessed proposal ancestry.
The earlier parent-bound diagnostic remains separate.

Two actual figures are under `paper/figures/pre-scale-search-v1/`.
`manifest.json` binds their bytes and the retained report. From a committed
checkout with the approved project interpreter:

```text
.venv/bin/python -m scripts.reports.pre_scale_search_reproduce_v1 --report research/data/pre-scale-search-v1/report.json --manifest research/data/pre-scale-search-v1/manifest.json --figures paper/figures/pre-scale-search-v1 --output <fresh-independent-directory>
```

This recomputes all available physical cross-scores, all-slot paths, exact ties,
36 logical rows, summaries and 96 paired reference comparisons, then rebuilds
the report, PNG/SVG and CSV. It makes no model calls, executes no candidate
source and does not repeat the full raw audit or fresh inference. Raw journals,
weights and corpus remain outside Git; these are local research artifacts,
not redistribution clearance. The scientific interpretation is in
[the results note](../../results/pre-scale-search-v1.md).

All eight actual English development inspectors are retained under
`game-ui-v2/public/data/pre-scale-foundry-v1/`, each bound by its manifest.
For example, a locally running v2 UI opens
`/native.html?pre-scale-arm=efficiency%3Aparameters`. These are development
records, not three-seed evidence. The separate final progress projection is
`game-ui-v2/public/data/pre-scale-observatory.closed-v1.json`; the earlier
`pre-scale-observatory.actual.json` remains unchanged. To view this fixed closed
projection with the existing local-update route, copy it to the ignored
`pre-scale-observatory.latest.json` and open `/pre-scale.html?source=latest`.
The viewer sends only GET requests and never starts an experiment.
