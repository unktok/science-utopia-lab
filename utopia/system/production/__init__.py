"""Adapters from production ScienceUtopia mechanisms to generic graphs."""

from .evaluation import (
    CONFERENCE_ACCEPTANCE,
    register_conference_evaluation_mechanism,
)
from .funding import (
    COMPACT_RANKED_ALLOCATION,
    register_compact_funding_mechanism,
)
from .governance import (
    EVENT_RESPONSIVE_GOVERNMENT,
    POLICY_SCHEMA_VERSION,
    THRESHOLD_GOVERNMENT,
    parse_policy_decision,
    register_government_mechanisms,
)
from .publication import (
    PAPER_TRACKER_PUBLICATION,
    register_paper_tracker_publication_mechanism,
)


def register_production_mechanisms(registry) -> None:
    """Register every production adapter available to a generic graph."""

    register_compact_funding_mechanism(registry)
    register_conference_evaluation_mechanism(registry)
    register_paper_tracker_publication_mechanism(registry)
    register_government_mechanisms(registry)


__all__ = [
    "COMPACT_RANKED_ALLOCATION",
    "CONFERENCE_ACCEPTANCE",
    "EVENT_RESPONSIVE_GOVERNMENT",
    "PAPER_TRACKER_PUBLICATION",
    "POLICY_SCHEMA_VERSION",
    "THRESHOLD_GOVERNMENT",
    "parse_policy_decision",
    "register_compact_funding_mechanism",
    "register_conference_evaluation_mechanism",
    "register_paper_tracker_publication_mechanism",
    "register_government_mechanisms",
    "register_production_mechanisms",
]
