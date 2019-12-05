# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['api_uu_research_system_metadata']

@api.make()
def api_uu_research_system_metadata(ctx, coll):
    """Returns collection statistics as JSON."""

    import math

    def convert_size(size_bytes):
        if size_bytes == 0:
            return "0B"

        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return '{} {}'.format(s, size_name[i])

    data_count = collection.data_count(ctx, coll)
    collection_count = collection.collection_count(ctx, coll)
    size = collection.size(ctx, coll)
    size_readable = convert_size(size)

    result = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    return {"Package size": result}
