# Code-tested native loop: retained closed projections

`report.json`, `slots.csv` and `manifest.json` are exact bytes of the first
8bb712f export after two matching original93076b4 audits. A second fresh export
matches all seven files. `costs.json` is the exact independently reproduced
cost projection. Actual PNG/SVG files live in
`paper/figures/native-code-tested-loop-v1/`; the manifest binds their bytes.

These data retain all four slots, all three references, both unavailable
candidate losses, exact source-change paths, same-fixture later-code
comparisons and frozen selection ties. Reused seed61001 is development data.
The scope is neither a held-out policy evaluation nor an optimizer replication.
[Results and limits](../../results/native-code-tested-loop-v1.md).

Full cold reconstruction needs the ignored original raw993-file archive,
its original-source audits and the frozen source checkouts; it is not a
portable raw-free rerun or an anonymous submission bundle. From8bb712f use
`python -m scripts.reports.native_code_tested_loop_v1 --run <original-raw>
--audit-one <audit-1.json> --audit-two <audit-2.json> --output <fresh-path>`.
Use the approved environment/interpreter. It calls no model and executes no
candidate code. Relative figure/data directories above are repository paths;
original absolute provenance paths in the manifest remain historical.
