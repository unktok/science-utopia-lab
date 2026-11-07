# Local paper-rebuild subset

This is preparation for the submission goal, not a final reviewer/public bundle.
The current manuscript is a working draft. Its V2 results remain pending the
finite experiment and closed-source audits. Do not publish/upload this subset
or infer anonymous submission, human authorship or redistribution clearance.

At source37e5443 the actual local subset stages and builds offline successfully;
[verification receipt](../research/results/paper-rebuild-bundle-verification-v1.json).
All11 new pages were individually inspected, with identical rendered PNG bytes
and extracted text versus the reviewed original. PDF file bytes differ; no
unproven claim about the sole cause of that difference is made. This current
working-draft check must be repeated after final-result manuscript changes.

## Exact subset and actual scope

The [explicit allowlist](../research/publication/paper-rebuild-allowlist-v1.json)
contains12 exact paths: source, two bibliographies, template, two input tables,
three graphics, the reviewed PDF, its build receipt and LICENSE. There is no
glob or recursive copy of the checkout. Raw data, scientist replies, model
weights, game assets, operator settings and Git history are excluded.

[The staging tool](../scripts/reports/paper_rebuild_bundle.py) verifies a clean
committed checkout, tracked bytes, receipt-bound hashes and this manuscript's
literal TeX dependencies. It keeps original bytes and notices, records a
manifest and refuses an existing destination. A narrow UTF-8 home-path scan
reports locations, not secret values; it is not a secret/anonymity/rights audit.
The dependency parser handles current literal inputs, figures, bibliographies
and the local style. It is not a general TeX parser or a proof of TeX safety.
The actual build must use Tectonic's untrusted and offline/cache-only flags.

## Stage and rebuild

Use the approved uv-managed project interpreter, never Apple Python. The real
CLI must run after committing the tool/policy and without editing its source
or HEAD during the check. Choose a fresh destination outside this checkout or
under ignored outputs; do not use an experiment's raw directory.

```text
python -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-v1.json \
  --output <fresh-local-staging-directory>
```

Follow REBUILD.md inside that directory. Its command uses an existing Tectonic
cache, with no package/network fetch. Render the new PDF using Poppler and
inspect all pages. Keep the original reviewed PDF and receipts unchanged;
rebuild hashes may differ because of PDF metadata/cache/tool versions. Check
rendered pages and text rather than declaring byte identity without measuring it.
Record original/rebuilt source and PDF hashes, pages, tool versions, warnings,
render/visual checks and exact included inventory in a separate verification.

The receipt references scientific inputs deliberately omitted from this subset.
PDF rebuilding is not numerical recomputation, raw-evidence auditing or fresh
inference reproduction. It does not establish that a new machine without TeX
dependencies/cache can build offline. Those tiers remain separate in the
[research workflow](research-workflow.md).

## Before the actual final package

Update the allowlist/receipt after final V2 analysis and manuscript changes,
repeat staging/build/page inspection, then perform target-cycle format,
authorship/AI-use disclosure, metadata/link, attribution and rights review on
the actual files. A final anonymous copy, if appropriate, is a separate
explicit version; do not scrub immutable historical records or remove required
third-party notices. Numerical-analysis/source and access-controlled raw-audit
materials require their own exact dependency lists, not an unreviewed full clone.
External sharing and actual submission still require user approval.
