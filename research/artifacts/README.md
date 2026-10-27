# Artifact manifests

Raw simulation outputs remain outside Git. Each completed campaign should track
a compact manifest containing:

- campaign and protocol IDs
- source commit and study revision
- model, backend, and dataset identity
- compact result and registry hashes
- immutable bundle or inventory hash
- current raw-artifact locator
- backup/read-back verification date
- retention status

Historical absolute paths remain immutable provenance. Moving a repository or
artifact adds a `current_locator`; it does not rewrite the original manifest.

Current records:

- [`first-closed-loop-engineering-v1.manifest.json`](first-closed-loop-engineering-v1.manifest.json)
