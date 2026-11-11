# Local paper-rebuild subset

This page documents the historical11/12-page short-draft subsets, not a final
reviewer/public bundle. The latest [integrated manuscript](../paper/integrated-estimands-build-v1.json)
has its own source and56-page PDF. The historical empirical V2 manuscript and both full audits are complete, but
remain a working draft rather than a final reviewer package. Do not publish/upload this subset
or infer anonymous submission, human authorship or redistribution clearance.

At source37e5443 the actual local subset stages and builds offline successfully;
[verification receipt](../research/results/paper-rebuild-bundle-verification-v1.json).
All11 new pages were individually inspected, with identical rendered PNG bytes
and extracted text versus the reviewed original. PDF file bytes differ; no
unproven claim about the sole cause of that difference is made. This current
historical check concerns the old V1/S1 draft, not the new V2 paper.

The new [V2 allowlist](../research/publication/paper-rebuild-allowlist-v2.json)
has13 exact paths and10 literal TeX dependencies, bound to the V3 build receipt
and submission-v2.tex. It omits the compressed numerical report and raw worlds.
The original12-path policy and its earlier verification remain unchanged.
At clean e3f4ee7 the new V2 subset actually stages/builds offline; all12 new
rendered pages are individually reviewed and match the original PNG/text bytes.
PDF bytes differ. [Verification and limits](../research/results/native-design-v2-reproduction-verification-v1.json).

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

## Recover the historical input version

The shared bibliographies have changed since these short drafts were built.
Do not compare their old receipt hashes with today's working files or overwrite
an old receipt to make that check pass. The [reconstruction index](../paper/historical-source-reconstruction-v1.json)
identifies commit8027f568cc16b0aed7428eab593f716b19530b20, which supplies every
recorded input byte for all three variants. The old receipts did not record a
build commit; this is exact byte reconstruction, not original-build attestation.

Create a fresh detached worktree at that commit, then run its unchanged staging
tool with the corresponding v1, v2 or anonymous-v1 allowlist. November12 actual
staging succeeds with12/13/13 files and the [retained manifests](../research/data/historical-paper-reconstruction-v1/README.md).
No old TeX build or model inference is added by that extraction.

```text
git worktree add --detach <fresh-historical-checkout> 8027f568cc16b0aed7428eab593f716b19530b20
cd <fresh-historical-checkout>
```

## Stage and rebuild

Use the approved uv-managed project interpreter, never Apple Python. The real
CLI must run after committing the tool/policy and without editing its source
or HEAD during the check. Choose a fresh destination outside this checkout or
under ignored outputs; do not use an experiment's raw directory.

```text
<approved-project-python> -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-v2.json \
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
