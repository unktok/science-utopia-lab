"""All8 corrected four-step author sessions joined to actual native outcomes."""
from scripts.reports import native_priority_author_outcomes_v1 as base

PROFILE = 'corrected-choice-v1'
_, SCHEMA = base.profile_contract(PROFILE)
ROOT, METHODS, OBJECTIVES = base.ROOT, base.METHODS, base.OBJECTIVES
read, collect = base.read, base.collect


def join(report, authors): return base.join(report, authors, profile=PROFILE)


def export(args): return base.export(args, profile=PROFILE)


if __name__ == '__main__': base.main(profile=PROFILE)
