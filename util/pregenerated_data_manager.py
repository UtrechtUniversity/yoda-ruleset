"""This file contains functions for storing and retrieving local
   pregenerated data in Yoda."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os.path
from typing import Union

from config import config


def _get_file_path(name: str) -> str:
    if "/" in name or "." in name:
        raise Exception("Pregenerated data file name must not contain dots or slashes.")
    return os.path.join(config.pregenerated_data_dir, name)


def pregenerated_data_load(name: str) -> Union[dict, None]:
    """ Loads pregenerated data item

        :param name: name of the data item

        :returns: either a dictionary of data, or None if the item is not found
    """
    file_path = _get_file_path(name)
    if os.path.exists(file_path):
        with open(file_path, "r") as input:
            return json.load(input)
    else:
        return None


def pregenerated_data_save(name: str, data: dict) -> None:
    file_path = _get_file_path(name)
    with open(file_path, "w") as output:
        json.dump(data, output, ensure_ascii=False, indent=4)
