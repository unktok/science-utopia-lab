"""Wait for actual corrected paired readouts; export all8 author/outcome rows twice."""
from scripts import finish_native_priority_author_outcomes_v1 as base

PROFILE = 'corrected-choice-v1'
SCHEMA = 'scienceutopia.native-corrected-choice-author-outcomes-finish.v1'


def run(args): return base.run(args, profile=PROFILE)


if __name__ == '__main__': base.main(profile=PROFILE)
