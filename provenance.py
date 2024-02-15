# -*- coding: utf-8 -*-
"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import time

import genquery

import vault
from util import *

__all__ = ['rule_provenance_log_action',
           'rule_copy_provenance_log',
           'api_provenance_log']


@rule.make()
def rule_provenance_log_action(ctx, actor, coll, action):
    """Function to add action log record to provenance of specific folder.

    :param ctx:    Combined type of a callback and rei struct
    :param actor:  The actor of the action
    :param coll:   The collection the provenance log is linked to.
    :param action: The action that is logged.
    """
    try:
        log_item = [str(int(time.time())), action, actor]
        avu.associate_to_coll(ctx, coll, constants.UUPROVENANCELOG, json.dumps(log_item))
        vault.update_archive(ctx, coll)
        log.write(ctx, "rule_provenance_log_action: <{}> has <{}> (<{}>)".format(actor, action, coll))
    except Exception:
        log.write(ctx, "rule_provenance_log_action: failed to log action <{}> to provenance".format(action))


def log_action(ctx, actor, coll, action, update=True):
    """Function to add action log record to provenance of specific folder.

    :param ctx:    Combined type of a callback and rei struct
    :param actor:  The actor of the action
    :param coll:   The collection the provenance log is linked to.
    :param action: The action that is logged.
    :param update: Whether to update provenance in any archive (default: True)
    """
    try:
        log_item = [str(int(time.time())), action, actor]
        avu.associate_to_coll(ctx, coll, constants.UUPROVENANCELOG, json.dumps(log_item))
        if update:
            vault.update_archive(ctx, coll)
        log.write(ctx, "rule_provenance_log_action: <{}> has <{}> (<{}>)".format(actor, action, coll))
    except Exception:
        log.write(ctx, "rule_provenance_log_action: failed to log action <{}> to provenance".format(action))


@rule.make()
def rule_copy_provenance_log(ctx, source, target):
    """Copy the provenance log of a collection to another collection.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    provenance_copy_log(ctx, source, target)


def provenance_copy_log(ctx, source, target):
    """Copy the provenance log of a collection to another collection.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    try:
        # Retrieve all provenance logs on source collection.
        iter = genquery.row_iterator(
            "order_desc(META_COLL_ATTR_VALUE)",
            "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_action_log'" % (source),
            genquery.AS_LIST, ctx
        )

        # Set provenance logs on target collection.
        for row in iter:
            avu.associate_to_coll(ctx, target, constants.UUPROVENANCELOG, row[0])

        log.write(ctx, "rule_copy_provenance_log: copied provenance log from <{}> to <{}>".format(source, target))
    except Exception:
        log.write(ctx, "rule_copy_provenance_log: failed to copy provenance log from <{}> to <{}>".format(source, target))


def get_provenance_log(ctx, coll):
    """Return provenance log of a collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of a collection in research or vault space.

    :returns: Provenance log as a list
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
def api_provenance_log(ctx, coll):
    """Return formatted provenance log of a collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of a collection in research or vault space.

    :returns: Formatted provenance log as a list
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


def latest_action_actor(ctx, path):
    """Return the actor of the latest provenance action.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of a collection in research or vault space.

    :returns: Actor of latest provenance action
    """
    provenance_log = get_provenance_log(ctx, path)
    return provenance_log[-1][2]
