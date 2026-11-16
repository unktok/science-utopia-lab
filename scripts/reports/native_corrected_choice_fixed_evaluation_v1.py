"""Both corrected frozen endpoint scopes, every condition and all60 contrasts."""
from pathlib import Path

from scripts.reports import native_priority_fixed_evaluation_v1 as base
from scripts.run_native_corrected_choice_fixed_evaluation_v1 import SCHEMA as STUDY, SEEDS, PROFILE

SCHEMA = 'scienceutopia.native-corrected-choice-fixed-evaluation-readout.v1'
METRICS, INSTRUMENT = base.METRICS, base.INSTRUMENT


def contrast_definitions(bank): return base.contrast_definitions(bank, profile=PROFILE)


def summarize(plan, audit): return base.summarize(plan, audit, profile=PROFILE)


def export(args): return base.export(args, profile=PROFILE)


if __name__ == '__main__': base.main(profile=PROFILE, worker_path=Path(__file__))
