"""Exact corrected all8 paired author/outcome provenance plus actual body phases."""
from scripts.reports import export_native_author_visibility_v1 as base

PROFILE = 'corrected-choice-v1'
SCHEMA = 'scienceutopia.native-corrected-choice-author-visibility-export.v1'


def export(args): return base.export(args, profile=PROFILE)


if __name__ == '__main__': base.main(profile=PROFILE)
