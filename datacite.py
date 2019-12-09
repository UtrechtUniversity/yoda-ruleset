# -*- coding: utf-8 -*-
"""Functions for communicating with DataCite and some utilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import random
import string

from util import *

__all__ = ['rule_uu_generate_random_id']


def generate_random_id(ctx, length):
    """Generate random ID for DOI."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for x in range(int(length)))

rule_uu_generate_random_id = rule.make(inputs=[0], outputs=[1])(generate_random_id)
