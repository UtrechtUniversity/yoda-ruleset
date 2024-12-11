"""Functions for communicating with DataCite and some utilities."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import random
import string
from typing import Dict

import requests

from util import *


def metadata_post(payload: Dict) -> int:
    """Register DOI metadata with DataCite."""
    url = "{}/dois".format(config.datacite_rest_api_url)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.post(url,
                             auth=auth,
                             data=payload.encode(),
                             headers=headers,
                             timeout=30,
                             verify=config.datacite_tls_verify)

    return response.status_code


def metadata_put(doi: str, payload: str) -> int:
    """Update metadata with DataCite."""
    url = "{}/dois/{}".format(config.datacite_rest_api_url, doi)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.put(url,
                            auth=auth,
                            data=payload.encode(),
                            headers=headers,
                            timeout=30,
                            verify=config.datacite_tls_verify)

    return response.status_code


def metadata_get(doi: str) -> int:
    """Check with DataCite if DOI is available."""
    url = "{}/dois/{}".format(config.datacite_rest_api_url, doi)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.get(url,
                            auth=auth,
                            headers=headers,
                            timeout=30,
                            verify=config.datacite_tls_verify)

    return response.status_code


def generate_random_id(length: int) -> str:
    """Generate random ID for DOI."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for x in range(int(length)))
