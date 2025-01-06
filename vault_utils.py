"""Utility functions for vault module."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List, Union


def get_copy_folder_to_vault_irsync_command(coll: str, target: str, vault_resource: Union[str, None], multi_threading: bool) -> List[str]:
    """Internal function to determine rsync command for copy-to-vault

       :param coll: source collection
       :param target: target collection
       :param vault_resource: resource to store vault data on (can be None)
       :param multi_threading: if set to false, disable multi threading,
                               otherwise use server default

       :returns: irsync command with parameters in list format
    """

    irsync_command: List[str] = ["irsync", "-rK"]

    if vault_resource is not None:
        irsync_command.extend(["-R", vault_resource])

    if not multi_threading:
        irsync_command.extend(["-N", "0"])  # 0 means no multi threading

    irsync_command.extend(["i:{}/".format(coll), "i:{}/original".format(target)])
    return irsync_command
