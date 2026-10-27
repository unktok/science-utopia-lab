# ADR 0006: Repository and artifact layout

Date: 2026-10-27
Status: accepted

## Context

The repository and three linked worktrees lived directly under the home
directory. Raw experiment outputs occupy about 1.3 GB, caches and model data are
larger, and historical manifests contain absolute paths.

## Decision

- The canonical repository lives at
  `/Users/shiro/unktok/dev/science-utopia-lab`.
- Linked development worktrees live under
  `/Users/shiro/unktok/dev/science-utopia-lab-worktrees/`.
- Temporary compatibility symlinks remain at the former
  `/Users/shiro/ScienceUtopia*` paths.
- Raw outputs, caches, and virtual environments remain outside Git.
- Each completed campaign tracks compact results, hashes, a historical locator,
  and a separately updateable current locator.
- `main` is the integration/research-record branch; long experiments run from a
  clean commit-pinned worktree.

## Consequences

Historical provenance is not rewritten during relocation. Compatibility links
can be removed only after old path references and environment entry points are
retired or rebuilt. Artifact durability beyond the local disk remains a future
backup task.
