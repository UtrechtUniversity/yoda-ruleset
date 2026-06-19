"""Utility functions for publication."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import Dict

import datacite
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


def generate_preliminary_doi(publication_config: Dict, publication_state: Dict) -> None:
    """Generate a preliminary DOI. Preliminary, because we check for collision later.

    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    datacite_prefix = publication_config["dataCitePrefix"]
    yoda_prefix = publication_config["yodaPrefix"]
    random_id = datacite.generate_random_id(publication_config["randomIdLength"])

    publication_state["randomId"] = random_id
    publication_state["versionDOI"] = f"{datacite_prefix}/{yoda_prefix}-{random_id}"


def generate_base_doi(publication_config: Dict, publication_state: Dict) -> None:
    """Generate a base DOI.

    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    datacite_prefix = publication_config["dataCitePrefix"]
    yoda_prefix = publication_config["yodaPrefix"]
    random_id = datacite.generate_random_id(publication_config["randomIdLength"])

    publication_state["baseRandomId"] = random_id
    publication_state["baseDOI"] = f"{datacite_prefix}/{yoda_prefix}-{random_id}"
