"""Frozen 51d9 backend, separately pinned latest UI; no worker is started."""
from pathlib import Path
import runpy

BACKEND = Path('/Users/shiro/unktok/dev/science-utopia-lab-worktrees/foundry-v15-a2-actual-view')
UI = Path('/Users/shiro/unktok/dev/science-utopia-lab-worktrees/foundry-v15/game-ui-v2/dist')
module = runpy.run_path(str(BACKEND / 'scripts/serve_native_lab.py'))
original = module['make_server']

def with_separate_ui(queue, **kwargs):
    kwargs['directory'] = UI
    return original(queue, **kwargs)

module['main'].__globals__['make_server'] = with_separate_ui
module['main']()
