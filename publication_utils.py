"""Utility functions for publication."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


def is_latest_version(publication_state: dict) -> bool:
    """Return True if this publication is the latest version."""
    previous_version = publication_state.get("previous_version")
    next_version = publication_state.get("next_version")
    return previous_version is not None and next_version is None
