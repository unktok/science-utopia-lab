"""Adapters from production ScienceUtopia mechanisms to generic graphs."""

from .funding import (
    COMPACT_RANKED_ALLOCATION,
    register_compact_funding_mechanism,
)

__all__ = [
    "COMPACT_RANKED_ALLOCATION",
    "register_compact_funding_mechanism",
]
