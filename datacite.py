# -*- coding: utf-8 -*-
"""Functions for communicating with DataCite and some utilities."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import random
import string

import requests

from util import *


def metadata_post(ctx, payload):
    """Register DOI metadata with DataCite."""
    url = "{}/dois".format(config.datacite_api_url)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.post(url, auth=auth, data=payload, headers=headers, timeout=30)

    return response.status_code


def metadata_put(ctx, doi, payload):
    """Update metadata with DataCite."""
    url = "{}/dois/{}".format(config.datacite_api_url, doi)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.put(url, auth=auth, data=payload, headers=headers, timeout=30)

    return response.status_code


def metadata_get(ctx, doi):
    """Check with DataCite if DOI is available."""
    url = "{}/dois/{}".format(config.datacite_api_url, doi)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}

    response = requests.get(url, auth=auth, headers=headers, timeout=30)

    return response.status_code


def generate_random_id(ctx, length):
    """Generate random ID for DOI."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for x in range(int(length)))

