# -*- coding: utf-8 -*-
"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time
from util import *

__all__ = ['rule_uu_provenance_log_action',
           'api_uu_provenance_log']


def rule_uu_provenance_log_action(rule_args, callback, rei):
    """Frontend function to add action log record to specific folder.

       :param actor: rodsaccount coming from yoda frontend
       :param folder: folder the logging is linked to
       :param action: the text that is logged

       :returns: string -- JSON object with status info
    """
    actor, folder, action = rule_args[0:3]

    # actor to be reformatted to yoda user - name#zone
    this_actor = actor.split(':')[0].replace('.', '#')

    status = 'Success'
    statusInfo = ''

    def report(x):
        # log.write(x)
        callback.writeString("stdout", x)

    callback.iiAddActionLogRecord(this_actor, folder, action)

    report(jsonutil.dump({'status':     status,
                          'statusInfo': statusInfo}))


def get_provenance_log(ctx, coll):
    """Returns provenance log of a collection.

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
    """Returns formatted provenance log of a collection.

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
