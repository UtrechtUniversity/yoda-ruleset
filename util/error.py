# -*- coding: utf-8 -*-
"""Common UU Error/Exception types."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


class UUError(Exception):
    """Generic Python rule error."""


class UUFileSizeError(UUError):
    """File size limit exceeded."""


class UUFileNotExistError(UUError):
    """File does not exist."""

class UUJsonValidationError(UUError):
    """JSON data could not be validated."""
