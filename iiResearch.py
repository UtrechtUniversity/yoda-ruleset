# \file      iiResearch.py
# \brief     Functions for the research space.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json


@define_as_rule('iiResearchSpaceSystemMetadata',
                inputs=[0], outputs=[1],
                transform=json.dumps, handler=RuleOutput.STDOUT)
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

    data_count = collection_data_count(callback, coll)
    collection_count = collection_collection_count(callback, coll)
    size = collection_size(callback, coll)
    size_readable = convert_size(size)

    result = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    return {"Package size": result}
