# Contributing to Science Utopia Lab

## Branch and worktree model

`main` is the integration and canonical research-record branch. Use one branch
and one linked worktree per feature or research track.

Suggested branch prefixes:

- `protocol/`: preregistration and campaign definitions
- `track/`: implementation tracks that can progress independently
- `experiment/`: commit-pinned execution preparation
- `results/`: compact outputs and interpretation after a campaign
- `fix/`: isolated correctness fixes

Only the coordinator edits shared indexes, the roadmap, and cross-track status.
Feature worktrees should remain directory-bounded where possible.

## Campaign lifecycle

1. Define `LossSpec`, design space, seed split, budget, and evaluation metrics.
2. Merge the protocol and create an annotated protocol tag.
3. Create a clean experiment worktree pinned to that tag or commit.
4. Run without editing the experiment worktree.
5. Commit compact results, hashes, manifests, and interpretation on a results
   branch; raw `outputs/` remains outside Git.
6. Create an annotated result tag after verification.

Changing a loss, simulator, evaluator, seed split, or decision rule creates a
new version. Do not overwrite a frozen protocol or historical result.

## Testing

Use the project environment:

```bash
.venv/bin/python -m pytest tests/optimization -q
```

Tests that declare deterministic CPU-only prerequisites must be invoked with
those prerequisites explicitly:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
  .venv/bin/python -m pytest -m 'not integration' -q
```

Never use Apple-provided Python or pip on this machine. Use
`/opt/homebrew/bin/uv` for environment management and the project `.venv` for
execution.

## Git remotes

- `origin`: writable project remote
- `upstream`: fetch-only source project

Push feature branches before long-running work. Merge one track at a time and
run its focused suite plus the shared regression suite after every integration.
