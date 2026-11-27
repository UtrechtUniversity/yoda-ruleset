"""Utility functions for vault module."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64
import binascii
import re
from dataclasses import dataclass
from typing import List, Optional, Union

from util import pathutil

# Name of the msiExecCmd script that copies a vault data package to research or deposit space.
COPY_TO_RESEARCH_SCRIPT = "admin-copy-to-research.sh"

# Group roles that allow writing in a research or deposit group (see groups.user_role).
_WRITE_ROLES = ("normal", "manager")

# Control characters are not allowed in decoded paths and user names.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


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


@dataclass(frozen=True)
class CopyToResearchRequest:
    """Decoded arguments of a copy-to-research request (see admin-copy-to-research.sh)."""

    origin:      str  # Vault collection to copy
    target:      str  # Collection to copy to (research or deposit space)
    receiver:    str  # User that receives the notifications and, for deposits, own access (user#zone)
    retry_count: int  # Attempt number, starts at 1


@dataclass(frozen=True)
class CopyToResearchFacts:
    """Facts about a copy-to-research request, looked up as the actor."""

    origin_readable:             bool  # Actor can see the origin collection
    actor_is_origin_datamanager: bool  # Actor is a data manager of the category of the origin vault group
    target_group_role:           str   # Role of the actor in the target group (see groups.user_role)
    target_exists:               bool  # Target collection exists
    target_parent_exists:        bool  # Parent of the target collection exists
    target_locked:               bool  # Target collection has locks
    target_parent_locked:        bool  # Parent of the target collection has locks
    target_has_data:             bool  # Target collection contains data objects


def _decode_b64_arg(token: str) -> str:
    """Decode one base64-encoded msiExecCmd argument.

    :param token: Base64-encoded argument

    :raises ValueError: If the argument is not valid base64 or not valid UTF-8

    :returns: Decoded argument
    """
    try:
        return base64.b64decode(token, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Argument is not valid base64-encoded UTF-8")


def parse_copy_to_research_args(args: str, actor: str) -> CopyToResearchRequest:
    """Parse and validate the msiExecCmd argument string of the copy-to-research script.

    The expected format is "<actor> <origin> <target> <receiver> <retry count>", where
    all arguments except the actor are base64-encoded, as constructed by
    schedule_copy_to_research in vault.py and iiAdminVaultCopyToResearch in iiVault.r.

    :param args:  Argument string, as passed to msiExecCmd
    :param actor: The user running msiExecCmd (user#zone)

    :raises ValueError: If the arguments are invalid. The message gives the reason.

    :returns: The decoded request
    """
    tokens = args.split(" ")
    if len(tokens) != 5 or "" in tokens:
        raise ValueError("Expected exactly 5 arguments separated by single spaces")

    actor_arg, origin_b64, target_b64, receiver_b64, retry_b64 = tokens
    if actor_arg != actor:
        raise ValueError("Actor not given as first argument")

    origin, target, receiver, retry_str = (_decode_b64_arg(t) for t in (origin_b64, target_b64, receiver_b64, retry_b64))

    if any(_CONTROL_CHARS.search(value) for value in (origin, target, receiver)):
        raise ValueError("Arguments contain control characters")

    if not retry_str.isdigit():
        raise ValueError("Retry count is not a number")

    sanity_check_results = get_sanity_checks_results_copy_to_research_paths(origin, target)
    if sanity_check_results:
        raise ValueError(" ".join(sanity_check_results))

    for path in (origin, target):
        if any(part in ("", ".") for part in path.split("/")[1:]):
            raise ValueError("Path contains empty or '.' components, or ends with a slash")

    return CopyToResearchRequest(origin=origin, target=target, receiver=receiver, retry_count=int(retry_str))


def copy_to_research_denial_reason(request: CopyToResearchRequest,
                                   actor: str,
                                   facts: CopyToResearchFacts) -> Optional[str]:
    """Decide whether a copy-to-research request matches what the vault and deposit modules do.

    The copy itself runs as rodsadmin, so this repeats the permission checks of the API
    functions that schedule it.

    :param request: Decoded request (see parse_copy_to_research_args)
    :param actor:   The user running msiExecCmd (user#zone)
    :param facts:   Facts about the request, looked up as the actor

    :returns: None if the copy is allowed, otherwise the reason for denying it
    """
    _, origin_zone, _, origin_subpath = pathutil.info(request.origin)
    target_space, target_zone, _, target_subpath = pathutil.info(request.target)
    actor_zone = actor.split("#")[-1]

    if origin_zone != actor_zone or target_zone != actor_zone:
        return "Origin, target and actor must be in the same zone"

    # The API functions schedule the first attempt as the user. Later attempts are
    # scheduled by rule_vault_copy_to_research, which runs as rodsadmin and so
    # skips this policy.
    if request.retry_count != 1:
        return "Only rodsadmin may schedule retries"

    # Notifications (and, for deposits, own access to the copy) go to the user who
    # requested the copy.
    if request.receiver != actor:
        return "Receiver must be the actor"

    # The actor must be allowed to read the data package. The API functions skip the
    # access check for data managers of the target group's category. Here that is
    # limited to data managers of the category that the origin vault group belongs to,
    # so a data manager can't copy packages from other categories.
    if origin_subpath == "":
        return "Origin must be a collection within a vault group"
    if not (facts.origin_readable or facts.actor_is_origin_datamanager):
        return "Actor has no access to the origin collection"

    if facts.target_group_role not in _WRITE_ROLES:
        return "Actor has no write access to the target group"

    # Copy of a vault data package (or a folder in it) into an existing research
    # folder, as a new subcollection named after the data package.
    # Needed for: api_vault_copy_to_research.
    if target_space is pathutil.Space.RESEARCH:
        if pathutil.basename(request.target) != pathutil.basename(request.origin):
            return "Target collection must be named after the origin collection"
        if not facts.target_parent_exists:
            return "Target folder does not exist"
        if facts.target_exists:
            return "Data package is already present in the target folder"
        if facts.target_parent_locked:
            return "Target folder is locked"
        return None

    # Copy of a vault data package into a newly created, empty deposit collection.
    # Needed for: api_deposit_copy_data_package.
    if target_space is pathutil.Space.DEPOSIT:
        if "/" in target_subpath or target_subpath == "":
            return "Target must be a deposit collection directly in the deposit group"
        if not facts.target_exists:
            return "Target deposit collection does not exist"
        if facts.target_has_data:
            return "Target deposit collection is not empty"
        if facts.target_locked:
            return "Target deposit collection is locked"
        return None

    # Already rejected by parse_copy_to_research_args (see the sanity checks).
    return "Target must be in research or deposit space"
