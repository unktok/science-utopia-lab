# Development setup

## Prerequisites

- Git
- Python 3.11 managed by `uv`
- Node.js for the buildless game UI tests
- Ollama with `qwen3:8b` only for local LLM integration work
- Linux/NVIDIA/vLLM only for the corresponding server path

Most unit tests require neither a GPU nor a running model server.

## Checkout and environment

```bash
git clone https://github.com/unktok/science-utopia-lab.git
cd science-utopia-lab
uv venv --python 3.11 --seed .venv
uv pip install --python .venv/bin/python -r requirements-test.txt
.venv/bin/python -m utopia --help
```

On the maintainer's macOS machine, follow the Python restrictions in
`AGENTS.md`: never invoke Apple-provided Python or pip. Use `/opt/homebrew/bin/uv`
and the repository `.venv`.

## Local simulator path

```bash
ollama pull qwen3:8b
scripts/run_macos_ollama.sh
```

Longitudinal runs are expensive. Do not start one to validate a routine code
change. Use unit tests, a dry run, or a preregistered smoke campaign first.

## Game UI

The current UI is buildless and reads a checked canonical replay payload:

```bash
~/.local/bin/python3 -m http.server 8000 --directory game-ui
```

Open <http://127.0.0.1:8000>. Regeneration and validation commands are in
[`game-ui/README.md`](../game-ui/README.md).

## Worktrees

Use a worktree when a feature runs in parallel with experiments or other
development:

```bash
git worktree add -b track/example ../science-utopia-example main
```

Never edit a commit-pinned experiment worktree during a campaign. Do not share
an output root, registry, or writable cache between experiment attempts unless
the relevant harness explicitly provides isolation and locking.

## Generated and local data

The following remain outside Git:

- `.venv/` and package caches;
- model and dataset caches;
- `outputs/` raw runs and logs;
- benchmark raw samples unless a protocol explicitly tracks them.

Commit schemas, protocols, compact JSON summaries, hashes, and human
interpretation instead.
