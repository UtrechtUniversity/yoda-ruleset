"""Utility functions for vault module."""

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List, Union

from util import pathutil


def get_copy_irsync_command(coll: str, target: str, vault_resource: Union[str, None], multi_threading: bool) -> List[str]:
    """Internal function to determine irsync command for copy-to-vault and copy-to-research.

    :param coll:            Source collection
    :param target:          Target collection
    :param vault_resource:  Resource to store data on (can be None)
    :param multi_threading: If False, disable multi threading, otherwise use server default

    :returns: irsync command with parameters in list format
    """
    irsync_command: List[str] = ["irsync", "-rK"]

    if vault_resource is not None:
        irsync_command.extend(["-R", vault_resource])

    if not multi_threading:
        irsync_command.extend(["-N", "0"])  # 0 means no multi threading

    irsync_command.extend([f"i:{coll}/", f"i:{target}"])

    return irsync_command


def get_sanity_checks_results_copy_to_research_paths(source: str, target: str) -> List[str]:
    """Internal function to determine whether a source and destination path for
       copying data from the vault pass sanity checks.

       :param source: source collection
       :param target: target collection

       :returns: list of sanity check fails (empty list means all tests passed)
    """
    failed: List[str] = []

    if not source.startswith("/"):
        failed.append("Source path is not absolute.")

    if not target.startswith("/"):
        failed.append("Target path is not absolute.")

    if ".." in source.split("/"):
        failed.append("Source path contains parent references (..)")

    if ".." in target.split("/"):
        failed.append("Target path contains parent references (..)")

    if len(failed) > 0:
        # The remaining tests assume absolute paths without parent references,
        # so skip these tests if previous tests did not pass.
        return failed

    (source_space, source_zone, source_group, _) = pathutil.info(source)
    (target_space, target_zone, target_group, _) = pathutil.info(target)

    if source_space != pathutil.Space.VAULT:
        failed.append("Source path not in vault group.")

    if target_space not in (pathutil.Space.DEPOSIT, pathutil.Space.RESEARCH):
        failed.append("Target path not in research or deposit group.")

    return failed


def get_sanity_checks_results_copy_to_vault_paths(source: str, target: str) -> List[str]:
    """Internal function to determine whether a source and destination path for
       archiving data in the vault pass sanity checks.

       :param source: source collection
       :param target: target collection

       :returns: list of sanity check fails (empty list means all tests passed)
    """
    failed: List[str] = []

    if not source.startswith("/"):
        failed.append("Source path is not absolute.")

    if not target.startswith("/"):
        failed.append("Target path is not absolute.")

    if ".." in source.split("/"):
        failed.append("Source path contains parent references (..)")

    if ".." in target.split("/"):
        failed.append("Target path contains parent references (..)")

    if len(failed) > 0:
        # The remaining tests assume absolute paths without parent references,
        # so skip these tests if previous tests did not pass.
        return failed

    (source_space, source_zone, source_group, _) = pathutil.info(source)
    (target_space, target_zone, target_group, _) = pathutil.info(target)

    if source_space not in (pathutil.Space.DEPOSIT, pathutil.Space.RESEARCH):
        failed.append("Source path not in research or deposit group.")

    if target_space != pathutil.Space.VAULT:
        failed.append("Target path not in vault group.")

    if (source_zone != target_zone
            or "-".join(source_group.split("-")[1:]) != "-".join(target_group.split("-")[1:])):
        failed.append("Source and target group are not in same compartment.")

    return failed
