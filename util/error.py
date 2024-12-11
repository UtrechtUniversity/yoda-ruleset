"""Common UU Error/Exception types."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


class UUError(Exception):
    """Generic Python rule error."""
    def __init__(self, message: str) -> None:
        self.message = message
        super(UUError, self).__init__(message)


class UUFileSizeError(UUError):
    """File size limit exceeded."""


class UUFileNotExistError(UUError):
    """File does not exist."""


class UUJsonValidationError(UUError):
    """JSON data could not be validated."""


class UUNotAuthorized(UUError):
    """Not authorized action."""
