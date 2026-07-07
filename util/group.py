"""Utility / convenience functions for querying group info."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List, Tuple, TYPE_CHECKING

import genquery

import user

if TYPE_CHECKING:
    import rule


def exists(ctx: 'rule.Context', grp: str) -> bool:
    """Check if a group with the given name exists.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: Boolean indicating if group with given name exists
    """
    return genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsgroup'"
                               .format(grp)).first() is not None


def members(ctx: 'rule.Context', grp: str) -> List[Tuple[str, str]]:
    """Get members of a given group.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: List of members of the group, where each list item is a tuple
              of username and zone name. The function returns an empty member
              list if the group does not exist.
    """
    query_results = list(genquery.Query(ctx, "USER_NAME, USER_ZONE",
                                        "USER_GROUP_NAME = '{}' AND USER_TYPE != 'rodsgroup'"
                                        .format(grp)))
    return list(query_results)


def is_member(ctx: 'rule.Context', grp: str, usr: str | None = None) -> bool:
    """Check if a group has a certain member.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name
    :param usr: Given user, otherwise client user is used

    :returns: Boolean indicating if group has a certain member
    """
    return user.is_member_of(ctx, grp, usr)


def get_category(ctx: 'rule.Context', grp: str) -> str | None:
    """Get the category of a group.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: Category of given group
    """
    ret = ctx.uuGroupGetCategory(grp, '', '')
    x = ret['arguments'][1]
    return None if x == '' else x


def get_research_groups_list(ctx: 'rule.Context') -> List[str]:
    """Returns a list of research groups

    :param ctx: Combined type of a callback and rei struct

    :returns: Category of given group
    """
    iter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_GROUP_NAME like 'research-%'",
        genquery.AS_LIST, ctx
    )
    return [row[0] for row in iter]
