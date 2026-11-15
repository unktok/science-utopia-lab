# Reviewed100-page rebuild preparation

The retained JUnit covers27 passing source/allowlist staging checks at997629ce,
including the real historical100-page input blobs and deliberate corruption
rejection. No TeX, PDF rendering, model, native world or generated code runs in
these tests. The production CLI later stages82 exact files at a6e83485; that is
file reconstruction, not a verified PDF rebuild or independent numerical rerun.

See the [preparation record](../../results/integrated-terminal-rebuild-subset-preparation-v1.json)
for the original setup failure, successful fresh staging, exact hashes and
remaining post-inference build/visual checks. Original PDF and receipts are
unchanged; raw worlds, weights and model replies are not bundled or published.
