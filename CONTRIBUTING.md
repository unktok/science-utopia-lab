# Contributing to Science Utopia Lab

Thank you for helping build Science Utopia Lab. Begin with the
[documentation index](docs/README.md), [architecture](docs/architecture.md),
and [current program status](research/STATUS.md). Scientific changes should
also read the [research workflow](docs/research-workflow.md).

## Development setup

Use Python 3.11 in a repository-local environment. This project prefers `uv`
for environment and dependency management:

```bash
uv venv --python 3.11 --seed .venv
uv pip install --python .venv/bin/python -r requirements-test.txt
.venv/bin/python -m utopia --help
```

Do not commit `.venv/`, caches, model weights, or `outputs/`. See the
[development guide](docs/development.md) for local Ollama and Linux/vLLM
variants.

## Branch and worktree model

`main` is the integration and canonical research-record branch. Use one branch
and, for concurrent or long-running work, one linked worktree per feature or
research track. Local checkout paths are not part of the project contract and
must not be hard-coded into source or contributor documentation.

Suggested branch prefixes:

- `protocol/`: preregistration and campaign definitions
- `track/`: implementation tracks that can progress independently
- `experiment/`: commit-pinned execution preparation
- `results/`: compact outputs and interpretation after a campaign
- `fix/`: isolated correctness fixes

Only the coordinator edits shared indexes, the roadmap, and cross-track status.
Feature worktrees should remain directory-bounded where possible.

Example:

```bash
git switch main
git pull --ff-only
git worktree add -b track/my-feature ../science-utopia-my-feature main
```

Keep commits reviewable: separate mechanical moves, generated artifacts,
implementation, and scientific interpretation when practical.

## Architecture boundaries

- `SystemSpec` is the whole science-system design object.
- A mechanism such as evaluation, funding, or publication is one optional
  component, not the root abstraction.
- The optimizer sees opaque candidate JSON and versioned loss observations; it
  must not depend on simulator internals.
- Held-out evaluation metrics do not update the same optimization campaign.
- The browser game renders canonical replay payloads and must not reimplement
  scientific state transitions.

See [architecture](docs/architecture.md) for the current implementation status.

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

Run the focused suite for your change, then the shared regression suites. UI
changes also run the Node tests. Exact commands and the current known-failure
baseline are in [docs/testing.md](docs/testing.md).

## Documentation and research records

- `docs/` explains how to build and work on the software.
- `research/` is the scientific record: protocols, decisions, runs, compact
  results, interpretation, and literature notes.
- Do not silently rewrite a frozen protocol or generated result.
- Generated reports use `.generated.md`; human interpretation is separate.
- Raw outputs remain outside Git; track compact manifests, hashes, and locators.
- Update `research/STATUS.md` only when the implementation or evidence actually
  changed.

## Pull requests

Every pull request should state:

- what changed and why;
- which boundary or research object it affects;
- tests run and known limitations;
- whether schemas, protocols, generated artifacts, or compatibility changed;
- whether the change requires a new campaign revision.

Use the repository pull-request template. Reviewers should be able to reproduce
the focused validation without an LLM or GPU unless the PR explicitly changes
an integration path.

## Git remotes

- `origin`: writable project remote
- `upstream`: fetch-only source project

Push feature branches before long-running work. Merge one track at a time and
run its focused suite plus the shared regression suite after every integration.
