"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import time
from typing import List

import genquery
from tstrings import t

import vault
from util import *

__all__ = ['rule_provenance_log_action',
           'rule_copy_provenance_log',
           'api_provenance_log']


@rule.make()
def rule_provenance_log_action(ctx: rule.Context, actor: str, coll: str, action: str) -> None:
    """Function to add action log record to provenance of specific folder.

    :param ctx:    Combined type of a callback and rei struct
    :param actor:  The actor of the action
    :param coll:   The collection the provenance log is linked to.
    :param action: The action that is logged.
    """
    log_action(ctx, actor, coll, action, update=True)


def log_action(ctx: rule.Context, actor: str, coll: str, action: str, update: bool = True) -> None:
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
        log.write(ctx, f"log_action: <{actor}> has <{action}> (<{coll}>)")
    except Exception:
        log.write(ctx, f"log_action: failed to log action <{action}> to provenance")


@rule.make()
def rule_copy_provenance_log(ctx: rule.Context, source: str, target: str) -> None:
    """Copy the provenance log of a collection to another collection.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    provenance_copy_log(ctx, source, target)


def provenance_copy_log(ctx: rule.Context, source: str, target: str) -> None:
    """Copy the provenance log of a collection to another collection.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    try:
        # Retrieve all provenance logs on source collection.
        logs = list(genquery.Query(
            ctx, "order_desc(META_COLL_ATTR_VALUE)",
            t("COLL_NAME = '{source}' AND META_COLL_ATTR_NAME = 'org_action_log'"),
            output=genquery.AS_LIST
        ))

        # Set provenance logs on target collection.
        for row in logs:
            avu.associate_to_coll(ctx, target, constants.UUPROVENANCELOG, row[0])

        log.write(ctx, f"rule_copy_provenance_log: copied provenance log from <{source}> to <{target}>")
    except Exception:
        log.write(ctx, f"rule_copy_provenance_log: failed to copy provenance log from <{source}> to <{target}>")


def get_provenance_log(ctx: rule.Context, coll: str) -> List:
    """Return provenance log of a collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of a collection in research or vault space.

    :returns: Provenance log as a list
    """
    provenance_log = []

    # Retrieve all provenance logs on a folder.
    logs = list(genquery.Query(
        ctx, "order_desc(META_COLL_ATTR_VALUE)",
        t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = 'org_action_log'"),
        output=genquery.AS_LIST
    ))

    for row in logs:
        log_item = jsonutil.parse(row[0])
        provenance_log.append(log_item)

    return provenance_log


@api.make()
def api_provenance_log(ctx: rule.Context, coll: str) -> api.Result:
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


def latest_action_actor(ctx: rule.Context, path: str) -> str:
    """Return the actor of the latest provenance action.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of a collection in research or vault space.

    :returns: Actor of latest provenance action
    """
    provenance_log = get_provenance_log(ctx, path)
    return provenance_log[-1][2]
