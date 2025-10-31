"""Gift tax calculation utilities package."""

from .calculator import GiftInput, GiftBreakdown, compute_tax, load_law_table

__all__ = [
    "GiftInput",
    "GiftBreakdown",
    "compute_tax",
    "load_law_table",
]
