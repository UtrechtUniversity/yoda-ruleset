# -*- coding: utf-8 -*-
"""Functions for communicating with DataCite and some utilities."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import random
import requests
import string

from util import *

__all__ = ['rule_uu_generate_random_id',
           'rule_uu_register_doi_metadata',
           'rule_uu_register_doi_url']


@rule.make(inputs=[0], outputs=[1])
def rule_uu_generate_random_id(ctx, length):
    """Generate random ID for DOI."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for x in range(int(length)))


@rule.make(inputs=[0], outputs=[1])
def rule_uu_register_doi_metadata(ctx, payload):
    """Register DOI metadata with DataCite.."""
    url = "{}/metadata".format(config.datacite_url)
    auth = (config.datacite_username, config.datacite_password)
    headers = {'Content-Type': 'application/xml', 'charset': 'UTF-8'}

    response = requests.post(url, auth=auth, data=payload, headers=headers)

    return response.status_code


@rule.make(inputs=[0,1], outputs=[2])
def rule_uu_register_doi_url(ctx, doi, url):
    """Register DOI url with DataCite."""
    url = "{}/doi".format(config.datacite_url)
    auth = (config.datacite_username, config.datacite_password)
    payload = "doi={}\nurl={}".format(doi, url)
    headers = {'content-type': 'text/plain', 'charset': 'UTF-8'}

    response = requests.post(url, auth=auth, data=payload, headers=headers)

    return response.status_code
