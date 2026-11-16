"""Fixed evaluation of both corrected endpoint scopes; no new design/reselection.

Implemented prospectively. Requires actual native public/cold verification and
normal original scientific closure before any real dispatch.
"""
from scripts import run_native_priority_fixed_evaluation_v1 as base

PROFILE = 'corrected-choice-v1'
ROOT, SEEDS = base.ROOT, base.SEEDS
SCHEMA, PROTOCOL, _, _, _ = base.profile_contract(PROFILE)
read = base.read
save = base.save
utc = base.utc
native_sources = base.native_sources
evidence_files = base.evidence_files
seeded_anchor = base.seeded_anchor
interval = base.interval
observe = base.observe
additional_from_checkpoints = base.additional_from_checkpoints
strict_inventory = base.strict_inventory


def origin_evidence(origin): return base.origin_evidence(origin, profile=PROFILE)


def build_plan(*args, **kwargs): return base.build_plan(*args, **kwargs, profile=PROFILE)


def require_plan(root): return base.require_plan(root, profile=PROFILE)


def prepare(args): return base.prepare(args, profile=PROFILE)


def run(root): return base.run(root, profile=PROFILE)


if __name__ == '__main__': base.main(profile=PROFILE)
