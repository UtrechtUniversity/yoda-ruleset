# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['rule_uu_research_system_metadata']


def research_collection_metadata(callback, coll):
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

    data_count = collection.data_count(callback, coll)
    collection_count = collection.collection_count(callback, coll)
    size = collection.size(callback, coll)
    size_readable = convert_size(size)

    result = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    return {"Package size": result}

rule_uu_research_system_metadata = rule.make(inputs=[0], outputs=[1],
                                          transform=jsonutil.dump, handler=rule.Output.STDOUT) \
                                         (research_collection_metadata)
