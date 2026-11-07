# Repository map and maintenance rules

The project has one research program, not a new project for every pilot version.
Use the short entry points below; versioned files are evidence, not competing
active roadmaps.

## Ownership of information

| Location | Responsibility |
| --- | --- |
| `README.md` | contributor entrance and honest current scope |
| `RESEARCH.md` | durable research purpose and original goals |
| `research/STATUS.md` | concise current capability/evidence state |
| `research/program-map.md` | goal-to-implementation/evidence mapping |
| `research/roadmap.md` | prioritized next work |
| `docs/` | development, architecture, testing and operations |
| `research/protocols/` | versioned prospective protocols |
| `research/results/`, `logbook/`, `decisions/` | data summaries, interpretation and decisions |
| `utopia/system/` | SystemSpec, execution and native extension boundaries |
| `utopia/optimization/` | loss, proposals, observations and search state |
| `utopia/replay/`, `game-ui-v2/` | canonical evidence and English game UI |
| `paper/` | manuscript and figures, not source of experiment truth |
| ignored `outputs/`, `.cache/`, `.venv/` | raw evidence and machine-local runtime data |

## Forward-only cleanup

Historical protocols/results/component files keep their paths. Frozen source
checkouts, detached experiment worktrees, raw responses and certificates must
not be moved, reformatted, deleted or relabeled during housekeeping.

The pre-reset README, research overview, index, status, roadmap and program map
are exact same-directory snapshots named `*history-through-v45.md`. Their
relative links still resolve from the same parent. The
[snapshot manifest](../research/results/repository-docs-reset-v1.json) records
source commit and byte hashes. Git history is retained too.

Entry points can be rewritten for clarity. Put detailed chronology in dated
logbooks and link it; never present a historical process as currently running.
A copy of a result is not another experiment.

## Checks

```bash
.venv/bin/python scripts/check_repository_docs.py
.venv/bin/python -m pytest tests/reports/test_repository_docs.py -q
```

The lightweight checker validates local inline Markdown link targets in active
entry documents and verifies historical snapshot byte hashes. It makes no
network request, imports no simulator/model, installs nothing and edits nothing.
It is not a complete Markdown renderer, remote-link checker or raw experiment audit.

## Branches and worktrees

Use focused feature branches and clean pinned experiment trees as described in
[CONTRIBUTING](../CONTRIBUTING.md). A large worktree count is not authorization
to prune evidence. Inspect ownership, uncommitted edits, source bindings and
artifact references before proposing removal. This cleanup deletes no branch,
worktree, output, environment or model.

Absolute operator paths may appear in historical manifests; new reusable source
and contributor commands must accept explicit paths instead of requiring one
person's home directory. Raw artifacts remain ignored, not silently uploaded.
