"""Utility functions for publication."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

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


def should_process(status: constants.publication_status) -> bool:
    """Return True if publication should process for this status."""
    return status in (
        constants.publication_status.UNKNOWN,
        constants.publication_status.RETRY,
    )


def should_return_early(status: constants.publication_status) -> bool:
    """Return True if publication should return early for this status."""
    return status in (
        constants.publication_status.UNRECOVERABLE,
        constants.publication_status.PROCESSING,
    )


def generate_preliminary_doi(publication_config: dict, publication_state: dict) -> None:
    """Generate a preliminary DOI. Preliminary, because we check for collision later.

    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    datacite_prefix = publication_config["dataCitePrefix"]
    yoda_prefix = publication_config["yodaPrefix"]
    random_id = datacite.generate_random_id(publication_config["randomIdLength"])

    publication_state["randomId"] = random_id
    publication_state["versionDOI"] = f"{datacite_prefix}/{yoda_prefix}-{random_id}"


def generate_base_doi(publication_config: dict, publication_state: dict) -> None:
    """Generate a base DOI.

    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    datacite_prefix = publication_config["dataCitePrefix"]
    yoda_prefix = publication_config["yodaPrefix"]
    random_id = datacite.generate_random_id(publication_config["randomIdLength"])

    publication_state["baseRandomId"] = random_id
    publication_state["baseDOI"] = f"{datacite_prefix}/{yoda_prefix}-{random_id}"


def generate_landing_page_url(publication_config: dict, publication_state: dict) -> None:
    """Generate a URL for the landing page.

    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    public_v_host = publication_config["publicVHost"]
    yoda_instance = publication_config["yodaInstance"]
    yoda_prefix = publication_config["yodaPrefix"]
    random_id = publication_state["randomId"]

    publication_state["landingPageUrl"] = f"https://{public_v_host}/{yoda_instance}/{yoda_prefix}/{random_id}.html"
