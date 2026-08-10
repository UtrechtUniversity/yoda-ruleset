"""Functions for communicating with DataCite and some utilities."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import random
import string

import requests

from util import *


def metadata_post(payload: dict) -> requests.Response:
    """Register DOI metadata with DataCite."""
    url = f"{config.datacite_rest_api_url}/dois"
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.post(url,
                             auth=auth,
                             data=payload.encode(),
                             headers=headers,
                             timeout=30,
                             verify=config.datacite_tls_verify)

    return response


def metadata_put(doi: str, payload: str) -> requests.Response:
    """Update metadata with DataCite."""
    url = f"{config.datacite_rest_api_url}/dois/{doi}"
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.put(url,
                            auth=auth,
                            data=payload.encode(),
                            headers=headers,
                            timeout=30,
                            verify=config.datacite_tls_verify)

    return response


def metadata_get(doi: str) -> requests.Response:
    """Check with DataCite if DOI is available."""
    url = f"{config.datacite_rest_api_url}/dois/{doi}"
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.get(url,
                            auth=auth,
                            headers=headers,
                            timeout=30,
                            verify=config.datacite_tls_verify)

    return response


def generate_random_id(length: int) -> str:
    """Generate random ID for DOI."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for x in range(int(length)))


def get_errors(response: dict) -> str:
    """Get errors from DataCite response"""
    error_msg = ''

    if 'errors' in response:
        errors = response['errors']
        for error in errors:
            if 'source' in error:
                error_msg += "DataCite error from attribute \"" + error['source'] + "\": \"" + error['title'] + "\". "
            else:
                error_msg += "DataCite error: \"" + error['title'] + "\". "

    return error_msg
