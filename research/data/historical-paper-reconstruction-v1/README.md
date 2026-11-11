# Historical short draft input reconstruction

Three old short-draft rebuild subsets have been extracted with the unchanged
original staging tool from a clean checkout at
8027f568cc16b0aed7428eab593f716b19530b20. The pilot has12 files; empirical V2
and its author-redacted variant each have13. These manifests retain the exact
original source, figure, bibliography, PDF and receipt hashes. The copied
bundles remain under ignored local outputs; only their compact manifests are
tracked here.

The reconstruction fixes a verification problem: historical receipts were
being checked against the changing shared working bibliography. Reading the
hash-matched Git blobs preserves the original receipts and PDFs while allowing
new manuscript references to be corrected.

The reconstruction commit supplies every recorded input byte. The original
receipts did not attest their build commit, so this does not establish that
the historical build actually ran at8027f56. This operation stages exact files;
it is not a fresh old-PDF build, numerical rerun, model inference or public
release. The author-redacted variant retains its original limited anonymity
and redistribution status.

The [source reconstruction index](../../../paper/historical-source-reconstruction-v1.json)
binds each unchanged receipt and the matching commit. The read-only
scripts.reports.historical_paper_sources reader checks each requested path and
original checksum. The tests inspect every bound historical blob and still
require the saved PDF bytes themselves to remain unchanged.

See [the rebuild instructions](../../../docs/paper-rebuild-bundle.md) for a
fresh checkout and destination. The latest integrated working paper has a
separate entrypoint, receipt and PDF; it does not overwrite these snapshots.
