# Local manuscript rebuild subsets

## Current native numeric manuscript

The [reviewed73-page draft](../paper/integrated-native-numeric-build-v1.json)
has38 figures,30 tables and26 references. Its
[explicit62-file subset](../research/publication/paper-rebuild-allowlist-integrated-native-numeric-v1.json)
stages at clean61da3a25 and builds using only the existing cache. Actual default-
mode extracted text and all73 rendered90dpi page PNGs match the reviewed draft.
The [verification](../research/results/integrated-native-numeric-rebuild-subset-verification-v1.json)
retains source/page/file hashes and an earlier mismatched extraction-mode check;
the layout-mode text is preserved, not overwritten to hide that QA error.
No PDF source or scientific outcome was changed to make the comparison pass.
PDF binary bytes differ. There are59 literal dependencies plus LICENSE,
reviewed PDF and receipt. This is not fresh inference, numerical/raw
reproduction, clean-machine installation, release clearance or readiness.

From that exact clean checkout and a fresh staging destination:

```text
<approved-project-python> -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-integrated-native-numeric-v1.json \
  --output <fresh-local-staging-directory>
```

Follow staged REBUILD.md; create its exact output parent before Tectonic runs.
Later live manuscript edits must not overwrite this frozen source identity.

## Preserved planning search manuscript

The [reviewed69-page planning search draft](../paper/integrated-planning-search-build-v1.json)
has a verified full-checkout cached build, source/evidence manifests and visual
review. Its [explicit58-file subset](../research/publication/paper-rebuild-allowlist-integrated-planning-search-v1.json)
also stages from cleanf4d0fe576fa1b5487ade490b7c0f7281a7d32b54 and builds
with only the existing cache. Extracted text and all69 rendered90dpi page
images match the reviewed artifact; pages1 and48 receive fresh visual checks.
The [verification](../research/results/integrated-planning-search-rebuild-subset-verification-v1.json)
retains every file/page hash and the first missing-output-directory build error,
followed by a successful unchanged-source build. PDF binary bytes differ.
The58 files include55 literal dependencies, LICENSE, reviewed PDF and receipt.
This is not numerical/raw reproduction, fresh inference or release clearance.
Use that exact checkout and a fresh destination:

```text
<approved-project-python> -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-integrated-planning-search-v1.json \
  --output <fresh-local-staging-directory>
```

Follow REBUILD.md and create the indicated output directory relative to the
staging root before building. The subsets below remain proofs of their own
older snapshots; none is silently substituted for the new69-page artifact.

## Preserved catalog planning manuscript

The [reviewed66-page draft](../paper/integrated-catalog-planning-build-v1.json)
now has its own [explicit54-file subset](../research/publication/paper-rebuild-allowlist-integrated-catalog-v1.json).
At clean e4bd2c767b13b0eb0342fc75d37de39331d0bfbb, the actual CLI stages
those exact files and Tectonic builds with only the existing cache. Extracted
text and all66 rendered90dpi page images match the reviewed artifact; pages1
and47 receive fresh visual spot checks. PDF bytes differ. The
[verification](../research/results/integrated-catalog-rebuild-subset-verification-v1.json)
retains exact source/manifest/tool hashes and every page hash. It is not a
numerical rerun, raw-data audit, anonymous package or release clearance.

Use that exact clean checkout to recover this snapshot after future edits:

```text
<approved-project-python> -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-integrated-catalog-v1.json \
  --output <fresh-local-staging-directory>
```

The54 files include51 literal dependencies, LICENSE, the original reviewed
PDF and its receipt. Only explicit manuscript inputs, illustrations, the UI
screenshot and printed table are included; no raw worlds, weights, replies or
numerical-analysis runtime are bundled. Follow the staged REBUILD.md and keep
the cache-only/untrusted build flags. This does not prove an offline build on
a fresh machine without the needed TeX cache.

## Preserved capacity manuscript

The [reviewed capacity snapshot](../paper/integrated-capacity-authority-build-v1.json)
has64 pages. Its [explicit51-file subset](../research/publication/paper-rebuild-allowlist-integrated-capacity-v1.json)
now stages and builds using only the existing TeX cache. Extracted text and
all64 rendered90dpi page PNGs match the reviewed artifact; pages1 and43 also
receive fresh visual spot checks. PDF binary bytes differ. The
[verification receipt](../research/results/integrated-capacity-rebuild-subset-verification-v1.json)
records the actual source, inventory and checks. This is a local PDF rebuild,
not numerical recomputation, a raw audit, an independent model rerun or a
release-cleared reviewer package.

The later66-page draft does not reuse this older allowlist as if live TeX
still matched. Historical staging tests reconstruct the exact old Git files
and continue to reject altered dependencies. Each snapshot keeps its own
PDF, source and minimal-subset verification.

Use the approved project interpreter from a clean committed checkout and a
fresh destination. To recover this exact64-page snapshot after later manuscript
edits, use a detached checkout of ef104f33f14b408fc48201757cff794a3db3c3b9;
do not overwrite its receipt or weaken a changed-input rejection:

```text
<approved-project-python> -m scripts.reports.paper_rebuild_bundle \
  --policy research/publication/paper-rebuild-allowlist-integrated-capacity-v1.json \
  --output <fresh-local-staging-directory>
```

Follow the staged REBUILD.md from its paper directory. The51 files contain
the literal manuscript dependencies, including its UI screenshot and printed
table, the upstream template/notices, original reviewed PDF and build receipt.
No raw worlds, model weights, private replies or numerical-analysis runtime
are copied. The new receipt adapter reconstructs original source/figure/support
hashes from the recorded Git commit and allows only literal normalized
repository-local parent inputs. It does not relax the old short-draft policies.

## Historical short drafts

The following11/12-page subsets retain their original identities. The
historical empirical V2 manuscript and both full audits are complete, but
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
