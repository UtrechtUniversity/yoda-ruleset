"""Functions for data object checksums."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import irods_types

from util import data_object, log, msi, rule

__all__ = ['rule_verify_checksum']


@rule.make()
def rule_verify_checksum(ctx: rule.Context, path: str) -> None:
    """Verify checksum of a data object, calculate checksum if it doesn't exist.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of data object to verify
    """
    if data_object.checksum(ctx, path):
        options = "verifyChksum="
    else:
        options = "ChksumAll=++++forceChksum="

    try:
        msi.data_obj_chksum(ctx, path, options, irods_types.BytesBuf())
        checksum = data_object.checksum(ctx, path)
        log.write(ctx, f"Verified checksum of <{path}>: {checksum}")
    except Exception as e:
        log.write(ctx, f"Could not verify checksum of <{path}>: {str(e)}")
