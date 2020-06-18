# -*- coding: utf-8 -*-
"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import time

from util import *

__all__ = ['rule_uu_provenance_log_action',
           'api_uu_provenance_log']


@rule.make()
def rule_uu_provenance_log_action(ctx, actor, coll, action):
    """
    Function to add action log record to provenance of specific folder.

    :param actor: The actor of the action
    :param coll: The collection the provenance log is linked to.
    :param action: The action that is logged.
    """
    log = {str(int(time.time())), actor, action}

    avu.set_on_coll(ctx, coll, constants.UUPROVENANCELOG, json.dumps(log))
    log.write(ctx, "rule_uu_provenance_log_action: <{}> has <{}> (<{}>)".format(actor, action, coll))


def get_provenance_log(ctx, coll):
    """
    Return provenance log of a collection.

    :param coll: Path of a collection in research or vault space.

    :returns dict: Provenance log.
    """
    provenance_log = []

    # Retrieve all provenance logs on a folder.
    iter = genquery.row_iterator(
        "order_desc(META_COLL_ATTR_VALUE)",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_action_log'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        log_item = jsonutil.parse(row[0])
        provenance_log.append(log_item)

    return provenance_log


@api.make()
def api_uu_provenance_log(ctx, coll):
    """
    Return formatted provenance log of a collection.

    :param coll: Path of a collection in research or vault space.

    :returns dict: Formatted provenance log.
    """
    provenance_log = get_provenance_log(ctx, coll)
    output = []

    for item in provenance_log:
        date_time = time.strftime('%Y/%m/%d %H:%M:%S',
                                  time.localtime(int(item[0])))
        action = item[1].capitalize()
        actor = item[2].split("#")[0]
        output.append([actor, action, date_time])

    return output
