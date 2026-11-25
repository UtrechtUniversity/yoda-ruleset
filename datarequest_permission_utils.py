"""Policy logic for temporary data request permission changes.

This module checks requests to run the admin-datarequest-temp-write-permission.sh
script (via msiExecCmd). That script changes ACLs as rodsadmin, so it must only make
changes that the data request module actually needs.

This module has no iRODS dependencies, so the logic can be unit tested. The caller
(py_acPreProcForExecCmd in policies.py) looks up the facts that need iRODS (roles of
the actor, status of the data request, group membership of the target user) and passes
them in.
"""

from __future__ import annotations

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from dataclasses import dataclass
from typing import Collection, Optional

# Name of the msiExecCmd script that this policy applies to.
TEMP_PERMISSION_SCRIPT = "admin-datarequest-temp-write-permission.sh"

# These values must match the constants and status values in datarequest.py.
# They are duplicated here so that this module does not depend on iRODS.
DRCOLLECTION         = "home/datarequests-research"
ATTACHMENTS_PATHNAME = "attachments"
DTA_PATHNAME         = "dta"
SIGDTA_PATHNAME      = "signed_dta"

# Files that a project manager may grant an assigned DAC member read access to.
REVIEWER_READABLE_FILES = frozenset({"datarequest.json", "preliminary_review.json", "datamanager_review.json"})

# Permission values that the data request module passes to the script.
ALLOWED_PERMISSIONS = frozenset({"grant", "grantread", "read", "revoke"})

# Characters that the msiExecCmd argument parser treats specially (quotes and
# backslashes), plus whitespace and control characters. Allowing them would let one
# argument string be split differently than this policy assumes. Quotes could also
# break out of the string literals that the script passes to irule.
_UNSAFE_CHARS = re.compile(r"""['"\\\s\x00-\x1f\x7f]""")

_USER_PATTERN = re.compile(r"^([^#/]+)#([^#/]+)$")

_PATH_PATTERN = re.compile(rf"^/([^/]+)/{re.escape(DRCOLLECTION)}/([0-9]+)(?:/(.+))?$")


@dataclass(frozen=True)
class TempPermissionRequest:
    """Parsed arguments of a temporary permission change request."""

    zone:        str            # Zone of the data request collection
    request_id:  str            # Data request ID
    subpath:     Optional[str]  # Path below the data request collection, or None for the collection itself
    permission:  str            # One of ALLOWED_PERMISSIONS
    target:      str            # User whose permission is changed (user#zone)
    target_name: str            # User name part of target
    is_self:     bool           # Whether target is the actor


def parse_temp_permission_args(args: str, actor: str) -> TempPermissionRequest:
    """Parse and validate the msiExecCmd argument string of the temporary permission script.

    The expected format is "<actor> <path> <permission> <user>", as constructed by
    adminTempWritePermission in uuDatarequests.r.

    :param args:  Argument string, as passed to msiExecCmd
    :param actor: The user running msiExecCmd (user#zone)

    :raises ValueError: If the arguments are invalid. The message gives the reason.

    :returns: The parsed request
    """
    tokens = args.split(" ")
    if len(tokens) != 4 or "" in tokens:
        raise ValueError("Expected exactly 4 arguments separated by single spaces")

    if any(_UNSAFE_CHARS.search(token) for token in tokens):
        raise ValueError("Arguments contain quotes, backslashes, whitespace or control characters")

    actor_arg, path, permission, target = tokens

    if actor_arg != actor:
        raise ValueError("Actor not given as first argument")

    actor_match = _USER_PATTERN.match(actor)
    if actor_match is None:
        raise ValueError("Invalid actor")

    target_match = _USER_PATTERN.match(target)
    if target_match is None:
        raise ValueError("Invalid target user")

    if permission not in ALLOWED_PERMISSIONS:
        raise ValueError(f"Permission <{permission}> is not used by the data request module")

    path_match = _PATH_PATTERN.match(path)
    if path_match is None:
        raise ValueError("Path is not within a data request collection")
    zone, request_id, subpath = path_match.groups()

    if subpath is not None and any(part in ("", ".", "..") for part in subpath.split("/")):
        raise ValueError("Path contains empty, '.' or '..' components")

    # Data request collections are only used within the zone of the actor.
    if zone != actor_match.group(2) or target_match.group(2) != zone:
        raise ValueError("Zone of path, actor and target user must be the same")

    return TempPermissionRequest(zone=zone,
                                 request_id=request_id,
                                 subpath=subpath,
                                 permission=permission,
                                 target=target,
                                 target_name=target_match.group(1),
                                 is_self=(target == actor))


def _is_reviewer_readable_file(subpath: Optional[str]) -> bool:
    """Whether a path below the request collection is a file that DAC reviewers may read."""
    if subpath is None:
        return False
    if subpath in REVIEWER_READABLE_FILES:
        return True
    parts = subpath.split("/")
    return len(parts) == 2 and parts[0] == ATTACHMENTS_PATHNAME


def _may_write_request_collection(roles: Collection[str], status: str) -> bool:
    """Whether the actor currently writes a file into the data request collection.

    This matches the callers of file_write() and file_lock() in datarequest.py.
    Those functions request write access to the request collection, and then
    revoke it (or downgrade it to read for the request owner). The status of the
    data request doesn't change in between.

    :param roles:  Data request roles of the actor (see datarequest_roles_get)
    :param status: Current status of the data request

    :returns: Whether the actor may get temporary write access to the request collection
    """
    # api_datarequest_preliminary_review_submit (also writes feedback for the researcher
    # via datarequest_feedback_write).
    if "PM" in roles and status == "SUBMITTED":
        return True

    # api_datarequest_datamanager_review_submit
    if "DM" in roles and status == "PRELIMINARY_ACCEPT":
        return True

    # api_datarequest_assignment_submit (also writes feedback for the researcher
    # via datarequest_feedback_write).
    if "PM" in roles and status in ("DATAMANAGER_ACCEPT", "DATAMANAGER_REJECT", "DATAMANAGER_RESUBMIT"):
        return True

    # api_datarequest_review_submit
    if "REV" in roles and status == "UNDER_REVIEW":
        return True

    # api_datarequest_evaluation_submit (also writes approval conditions and feedback
    # for the researcher via datarequest_feedback_write).
    if "PM" in roles and status in ("REVIEWED", "DAO_SUBMITTED"):
        return True

    # api_datarequest_preregistration_submit
    if "OWN" in roles and status == "APPROVED":
        return True

    return False


def temp_permission_denial_reason(request: TempPermissionRequest,
                                  roles: Collection[str],
                                  status: str,
                                  target_is_dac_member: bool,
                                  target_is_owner: bool) -> Optional[str]:
    """Decide whether a temporary permission change is needed by the data request module.

    :param request:              Parsed request (see parse_temp_permission_args)
    :param roles:                Data request roles of the actor (see datarequest_roles_get),
                                 e.g. "PM", "DM", "DAC", "OWN", "REV"
    :param status:               Current status of the data request (status value string)
    :param target_is_dac_member: Whether the target user is a member of the DAC group
    :param target_is_owner:      Whether the target user is the owner of the data request

    :returns: None if the change is allowed, otherwise the reason for denying it
    """
    subpath = request.subpath
    permission = request.permission

    # Read access for assigned DAC members to the documents they need to review.
    # Needed for: assign_request(), called by api_datarequest_assignment_submit.
    # The target may be the actor, if the project manager is also a DAC member.
    if _is_reviewer_readable_file(subpath):
        if (permission == "grantread"
                and "PM" in roles
                and status in ("DATAMANAGER_ACCEPT", "DATAMANAGER_REJECT", "DATAMANAGER_RESUBMIT")
                and target_is_dac_member
                and not target_is_owner
                and request.target_name != "rods"):
            return None
        return "Only a project manager may give assigned DAC members read access to review documents"

    # All other permission changes only apply to the actor.
    if not request.is_self:
        return "Not allowed to change permissions of another user"

    # Temporary write access to the data request collection, to write a file, and
    # revoking that access afterwards (or downgrading it to read access for the
    # request owner). Needed for: file_write() and file_lock(). See
    # _may_write_request_collection for the API functions that use these.
    if subpath is None:
        if permission == "grantread":
            return "Permission grantread is not used on the data request collection"
        if permission == "read" and "OWN" not in roles:
            return "Only the data request owner gets read access to the data request collection"
        if _may_write_request_collection(roles, status):
            return None
        return "Actor does not write to the data request collection in the current status"

    # Upload of attachments by the request owner: temporary write access, then
    # read access after the upload. Needed for: api_datarequest_attachment_upload_permission.
    if subpath == ATTACHMENTS_PATHNAME:
        if permission in ("grant", "grantread") and "OWN" in roles and status == "PENDING_ATTACHMENTS":
            return None
        return "Only the data request owner may upload attachments, and only while attachments are pending"

    # Upload of the DTA by a data manager: temporary write access, then revoking it.
    # Needed for: api_datarequest_dta_upload_permission.
    if subpath == DTA_PATHNAME:
        if (permission in ("grant", "revoke")
                and "DM" in roles
                and status in ("PREREGISTRATION_CONFIRMED", "DAO_APPROVED", "DTA_READY")):
            return None
        return "Only a data manager may upload the DTA, and only in the DTA phase"

    # Upload of the signed DTA by the request owner: temporary write access, then
    # read access after the upload. Needed for: api_datarequest_signed_dta_upload_permission.
    if subpath == SIGDTA_PATHNAME:
        if permission in ("grant", "grantread") and "OWN" in roles and status in ("DTA_READY", "DTA_SIGNED"):
            return None
        return "Only the data request owner may upload the signed DTA, and only in the DTA phase"

    return "Path is not used by the data request module for permission changes"
