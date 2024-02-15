# -*- coding: utf-8 -*-
"""Miscellaneous util functions."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import math


def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_name = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '{} {}'.format(s, size_name[i])
