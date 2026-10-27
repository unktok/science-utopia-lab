#!/usr/bin/env python3
"""CLI entry point for the metric-conditioned optimization study."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.optimization.metric_conditioned_study import main


if __name__ == "__main__":
    raise SystemExit(main())
