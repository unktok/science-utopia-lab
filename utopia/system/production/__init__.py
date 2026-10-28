"""Adapters from production ScienceUtopia mechanisms to generic graphs."""

from .communication import (
    KNOWLEDGE_BROADCAST,
    KNOWLEDGE_DIGEST,
    KNOWLEDGE_ITEM_SCHEMA_VERSION,
    KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
    KNOWLEDGE_RECEIVER,
    parse_knowledge_item,
    parse_knowledge_message,
    register_communication_mechanisms,
    validate_delivered_message,
)
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

    register_communication_mechanisms(registry)
    register_compact_funding_mechanism(registry)
    register_conference_evaluation_mechanism(registry)
    register_paper_tracker_publication_mechanism(registry)
    register_government_mechanisms(registry)


__all__ = [
    "COMPACT_RANKED_ALLOCATION",
    "CONFERENCE_ACCEPTANCE",
    "EVENT_RESPONSIVE_GOVERNMENT",
    "KNOWLEDGE_BROADCAST",
    "KNOWLEDGE_DIGEST",
    "KNOWLEDGE_ITEM_SCHEMA_VERSION",
    "KNOWLEDGE_MESSAGE_SCHEMA_VERSION",
    "KNOWLEDGE_RECEIVER",
    "PAPER_TRACKER_PUBLICATION",
    "POLICY_SCHEMA_VERSION",
    "THRESHOLD_GOVERNMENT",
    "parse_knowledge_item",
    "parse_knowledge_message",
    "parse_policy_decision",
    "register_communication_mechanisms",
    "register_compact_funding_mechanism",
    "register_conference_evaluation_mechanism",
    "register_paper_tracker_publication_mechanism",
    "register_government_mechanisms",
    "register_production_mechanisms",
    "validate_delivered_message",
]
