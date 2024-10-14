# -*- coding: utf-8 -*-
"""Miscellaneous util functions."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import math
import time
from collections import OrderedDict


def last_run_time_acceptable(found, last_run, config_backoff_time):
    """Return whether the last run time is acceptable to continue with task."""
    now = int(time.time())

    if found:
        # Too soon to run
        if now < last_run + config_backoff_time:
            return False

    return True


def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_name = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '{} {}'.format(s, size_name[i])


def remove_empty_objects(d):
    """Remove empty objects (None, '', {}, []) from OrderedDict."""
    if isinstance(d, dict):
        # Create OrderedDict to maintain order.
        cleaned_dict = OrderedDict()
        for k, v in d.items():
            # Recursively remove empty objects.
            cleaned_value = remove_empty_objects(v)
            # Only add non-empty values.
            if cleaned_value not in (None, '', {}, []):
                cleaned_dict[k] = cleaned_value
        return cleaned_dict
    elif isinstance(d, list):
        # Clean lists by filtering out empty objects.
        return [remove_empty_objects(item) for item in d if remove_empty_objects(item) not in (None, '', {}, [])]
    else:
        # Return the value abecause it is not a dict or list.
        return d
