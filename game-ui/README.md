# Game UI vertical slice

This is a local-only, buildless, read-only viewer for a canonical ScienceUtopia
replay. It does not run the simulator, an LLM, or a second implementation of
the replay state machine in the browser.

## Data boundary

```text
saved checkpoint + ledgers
  -> utopia.replay.convert_artifacts
  -> utopia.replay.replay (authoritative state projection)
  -> scripts/export_game_replay.py
  -> data/*.replay.json
  -> presentation-only browser UI
```

Each replay artifact contains the canonical events plus the authoritative
projected state at cursor zero and after every event. The UI may choose a visual
location for an active agent, but it does not calculate balances, publication
status, or other scientific state.

Regenerate the checked fixture:

```bash
PYTHONPATH=. ~/.local/bin/python3 scripts/export_game_replay.py \
  tests/replay/fixtures/one_year/checkpoint_year_1.json \
  --output game-ui/data/one-year.replay.json \
  --title "One Year at the Replay Institute" \
  --source-label tests/replay/fixtures/one_year
```

Serve it locally (a `file://` URL cannot fetch the replay artifact):

```bash
~/.local/bin/python3 -m http.server 8000 --directory game-ui
```

Then open <http://localhost:8000>. Keyboard controls are Left/Right to step,
Space to play/pause, and Home/End to jump.

## Validation

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/replay
node --test game-ui/test/model.test.mjs
```

## Scope boundary

This slice demonstrates replay and evidence inspection only. Intervention,
branch runs, cross-seed uncertainty, and editing a `SystemSpec` belong to later
slices and must call simulation/experiment APIs rather than introducing game
logic in the browser.
