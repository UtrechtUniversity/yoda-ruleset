"""Utility functions for processing differences between data."""

from __future__ import annotations

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from typing import Any, List

from deepdiff import DeepDiff


def describe_metadata_changes(data1: Any, data2: Any) -> List[str]:
    """Describe differences between two metadata data structures, typically
       a parsed JSON object

    :param data1:    First data structure
    :param data2:    Second data structure

    :returns:        List of strings describing the changes
    """
    try:
        results: List[str] = []
        meta_diff = DeepDiff(data1, data2)
        item_list = {}

        for i in meta_diff:
            action = i.split('_')[-1]
            item_list[action] = []
            if i.startswith('dictionary'):
                keys = meta_diff[i]
            else:
                keys = meta_diff[i].keys()
            if keys:
                for item in keys:
                    m = re.match(r"root\['(.*?)'\]", item)
                    if m:
                        item_list[action].append(m.group(1).replace('_', ' '))

        for item in item_list:
            if len(item_list[item]) < 5:
                list_of_changes = ', '.join(item_list[item])
                results.append(f"{item.replace('changed', 'modified')} metadata: {list_of_changes}")
            else:
                list_of_changes = ', '.join(item_list[item][:4])
                results.append(f"{item.replace('changed', 'modified')} metadata: {list_of_changes} and more")

        return results

    except Exception:
        return ["modified metadata"]
