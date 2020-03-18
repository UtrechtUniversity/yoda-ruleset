# -*- coding: utf-8 -*-
"""Functions for communicating with EPIC and some utilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import uuid

from util import *

__all__ = ['rule_uu_generate_uuid']


def generate_uuid(ctx):
    """Generate random ID for DOI."""
    randomuuid = str(uuid.uuid4())
    return randomuuid.upper()


rule_uu_generate_uuid = rule.make(inputs=[], outputs=[0])(generate_uuid)
