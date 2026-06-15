"""Functions for data object checksums."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64

import irods_types

from util import data_object, log, msi, rule

__all__ = ['rule_verify_checksum']


@rule.make()
def rule_verify_checksum(ctx: rule.Context, path: str) -> None:
    """Verify checksum of a data object, calculate checksum if it doesn't exist.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Base64-encoded path of data object to verify
    """
    # Decode the Base64-encoded path.
    try:
        decoded_path = base64.b64decode(path).decode('utf-8')
    except Exception as e:
        log.write(ctx, f"Failed to decode path parameter <{path}>: {str(e)}")
        return

    if not decoded_path or not decoded_path.startswith('/'):
        log.write(ctx, f"Invalid path after decoding: <{decoded_path}>")
        return

    if data_object.checksum(ctx, decoded_path):
        options = "verifyChksum="
    else:
        options = "ChksumAll=++++forceChksum="

    try:
        msi.data_obj_chksum(ctx, decoded_path, options, irods_types.BytesBuf())
        checksum = data_object.checksum(ctx, decoded_path)
        log.write(ctx, f"Verified checksum of <{decoded_path}>: {checksum}")
    except Exception as e:
        log.write(ctx, f"Could not verify checksum of <{decoded_path}>: {str(e)}")
