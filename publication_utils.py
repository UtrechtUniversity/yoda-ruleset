"""Utility functions for publication."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import constants


def is_latest_version(publication_state: dict) -> bool:
    """Return True if this publication is the latest version."""
    previous_version = publication_state.get("previous_version")
    next_version = publication_state.get("next_version")
    return previous_version is not None and next_version is None


def should_abort(status: constants.publication_status) -> bool:
    """Return True if publication should stop for this status."""
    return status in (
        constants.publication_status.UNRECOVERABLE,
        constants.publication_status.RETRY,
    )
