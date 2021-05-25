# coding=utf-8

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    # given,
    scenarios,
    then,
    # when,
)

scenarios('../../features/ui/ui_deposit.feature')
