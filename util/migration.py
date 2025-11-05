"""Utility / convenience function for migrating (de)published data packages."""

from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import genquery
from util import *


def get_migration_config(ctx: rule.Context, coll: str) -> bool:
    """Get migration key and its value if exists."""

    val = ''
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND  META_COLL_ATTR_NAME = '{}_enable_migration'".format(constants.UUORGMETADATAPREFIX),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        val = row[1]
    
    if val == 'yes':
        return True
    else:
        return False
