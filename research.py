# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import meta_form

from util import *

__all__ = ['api_uu_research_system_metadata',
           'api_uu_research_collection_details']


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


@api.make()
def api_uu_research_collection_details(ctx, path):
    """Returns details of a research collection."""

    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is a research group.
    space, _, group, _ = pathutil.info(path)
    if space != pathutil.Space.RESEARCH:
        return {}

    basename = pathutil.chop(path)[1]

    # Retrieve user type.
    member_type = meta_form.user_member_type(ctx, group, user.full_name(ctx))

    # Retrieve research folder status.
    status = meta_form.get_coll_status(ctx, path)

    # Check if user is datamanager.
    category = meta_form.group_category(ctx, group)
    is_datamanager = meta_form.user_is_datamanager(ctx, category, user.full_name(ctx))

    # Retrieve lock count.
    lock_count = meta_form.get_coll_lock_count(ctx, path)

    # Check if vault is accessible.
    vault_path = ""
    vault_name = group.replace("research-", "vault-", 1)
    if collection.exists(ctx, pathutil.chop(path)[0] + "/" + vault_name):
        vault_path = vault_name

    return {"basename": basename,
            "status": status,
            "member_type": member_type,
            "is_datamanager": is_datamanager,
            "lock_count": lock_count,
            "vault_path": vault_path}
