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
.venv/bin/python -m pip --version  # verify at least26.2.2 before fetching packages
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

## Current game UI and legacy viewer

The current English Phaser/Vite interface is in `game-ui-v2/`. With its Node
dependencies already installed, use a loopback-only development server:

```bash
cd game-ui-v2
npm run dev -- --host 127.0.0.1
```

See the [current UI guide](../game-ui-v2/README.md) for exact evidence/export
boundaries. This guide does not install Node dependencies or start a server.
The earlier buildless viewer is retained in
[`game-ui/`](../game-ui/README.md); it is not the latest Foundry interface.

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
