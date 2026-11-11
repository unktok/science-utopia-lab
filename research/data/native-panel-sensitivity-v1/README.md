# Fixed-record reviewer-panel readout sensitivity

This compact report covers the 44 complete physical worlds of the closed
62388a7 T/E study, with all five partial failures explicitly skipped rather
than imputed. It verifies A/Q/R from each original four-year checkpoint and
the whole raw inventory against full audit85d4698f.

The 217 reviewed and46 unreviewed accepted-decision records are not independent
papers or new world replications. Readout subsets reuse already observed scores;
they do not change publication, remove actual review cost, or execute an
institution. A uniform subset preserves the full-panel expected mean; the
extremes can require hindsight. This is not independent quality or a policy
effect. [Interpretation and actual figure](../../results/native-panel-sensitivity-v1.md).

`report.json` content SHA256:
`73d3df0c0bd0e0183775cb0cfd12dc0585cf0904fdb48294b3caf758eeb6aa6d`.
Two independent original-source reads and this retained third copy agree in
every byte. The raw-model/corpus data and full audit remain outside Git.

Rebuild from the original closed run/full audit:

```text
.venv/bin/python -m scripts.reports.native_panel_sensitivity_v1 --run <closed-run> --audit <original-full-audit> --frozen-source <original-clean-62388a7> --output <fresh-report.json>
.venv/bin/python -m scripts.figures.native_panel_sensitivity_v1 --report <report.json> --audit <original-full-audit> --output <fresh-figure-directory>
```

Both commands are read-only with respect to scientific evidence. They make no
model calls, run no candidate source and do not repeat the complete raw audit.
