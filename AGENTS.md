# Project agent instructions

- Start research work from `research/INDEX.md` and `research/STATUS.md`.
- Keep four concepts separate: optimization loss/objective, technical run
  validity, held-out evaluation metrics, and optional promotion policy.
- Historical Metric Constitution and confirmation vetoes are not default
  constraints for new optimization campaigns.
- Run long campaigns only from a clean, commit-pinned experiment worktree.
  Develop code in a separate feature worktree and never modify an active
  experiment worktree.
- Keep raw caches and outputs out of Git. Track compact results, hashes,
  manifests, protocols, and interpreted reports.
- Do not execute Apple-provided Python or pip. Use `.venv/bin/python`,
  `~/.local/bin/python3`, `~/.local/bin/pip3`, and `/opt/homebrew/bin/uv`.
