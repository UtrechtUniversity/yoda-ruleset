"""Utility / convenience functions for dealing with resources."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List, TYPE_CHECKING

import genquery

if TYPE_CHECKING:
    import rule


def exists(ctx: 'rule.Context', name: str) -> bool:
    """Check if a resource with a given name exists."""
    return len(list(genquery.row_iterator(
               "RESC_ID", f"RESC_NAME = '{name}'",
               genquery.AS_LIST, ctx))) > 0


def id_from_name(ctx: 'rule.Context', resc_name: str) -> str:
    """Get resource ID from resource name.

    :param ctx:     Combined type of a callback and rei struct
    :param resc_name: Name of resource

    :returns: Resource ID
    """
    return genquery.Query(ctx, ["RESC_ID"], f"RESC_NAME = '{resc_name}'").first()


def name_from_id(ctx: 'rule.Context', resc_id: str) -> str:
    """Get resource name from resource ID.

    :param ctx:     Combined type of a callback and rei struct
    :param resc_id: Resource ID

    :returns: Resource name
    """
    return genquery.Query(ctx, ["RESC_NAME"], f"RESC_ID = '{resc_id}'").first()


def get_parent_by_id(ctx: 'rule.Context', resc_id: str) -> str | None:
    """Get resource parent ID from resource ID

    :param ctx:     Combined type of a callback and rei struct
    :param resc_id: Resource ID

    :returns: Parent resource ID (or None if it has no parent)
    """
    result = genquery.Query(ctx, ["RESC_PARENT"], f"RESC_ID = '{resc_id}'").first()
    return None if result == "" else result


def get_parent_by_name(ctx: 'rule.Context', resc_name: str) -> str | None:
    """Get resource parent name from resource name

    :param ctx:       Combined type of a callback and rei struct
    :param resc_name: Resource name

    :returns: Parent resource name (or None if it has no parent)
    """
    resource_id = id_from_name(ctx, resc_name)
    parent_resource_id = get_parent_by_id(ctx, resource_id)
    return None if parent_resource_id is None else name_from_id(ctx, parent_resource_id)


def get_children_by_id(ctx: 'rule.Context', resc_id: str) -> List:
    """Get resource children IDs from resource ID

    :param ctx:     Combined type of a callback and rei struct
    :param resc_id: Resource ID

    :returns: list of child resource IDs
    """
    result = list(genquery.row_iterator(
                  "RESC_ID",
                  f"RESC_PARENT = '{resc_id}'",
                  genquery.AS_LIST, ctx))
    return [r[0] for r in result]


def get_children_by_name(ctx: 'rule.Context', resc_name: str) -> List:
    """Get resource children names from resource name

    :param ctx:       Combined type of a callback and rei struct
    :param resc_name: Resource name

    :returns: Parent resource name (or None if it has no parent)
    """
    resource_id = id_from_name(ctx, resc_name)
    child_resource_ids = get_children_by_id(ctx, resource_id)
    return [name_from_id(ctx, child_id) for child_id in child_resource_ids]


def get_type_by_id(ctx: 'rule.Context', resc_id: str) -> str:
    """Get resource type from resource ID

    :param ctx:     Combined type of a callback and rei struct
    :param resc_id: Resource ID

    :returns: Resource type (e.g. "passhru")
    """
    return genquery.Query(ctx, ["RESC_TYPE_NAME"], f"RESC_ID = '{resc_id}'").first()


def get_type_by_name(ctx: 'rule.Context', resc_name: str) -> str:
    """Get resource type from resource name

    :param ctx:       Combined type of a callback and rei struct
    :param resc_name: Resource name

    :returns: Resource type (e.g. "passthru")
    """
    return genquery.Query(ctx, ["RESC_TYPE_NAME"], f"RESC_NAME = '{resc_name}'").first()


def get_resource_names_by_type(ctx: 'rule.Context', resc_type: str) -> List:
    """Get resource names by type

    :param ctx:       Combined type of a callback and rei struct
    :param resc_type: Resource type (e.g. "passthru" or "unixfilesystem")

    :returns: List of matching resource names
    """
    result = list(genquery.row_iterator(
                  "RESC_NAME",
                  f"RESC_TYPE_NAME = '{resc_type}'",
                  genquery.AS_LIST, ctx))
    return [r[0] for r in result]


def get_all_resource_names(ctx: 'rule.Context') -> List:
    """Get a list of all resource names

    :param ctx: Combined type of a callback and rei struct

    :returns: list of all resource names
    """
    result = list(genquery.row_iterator(
                  "RESC_NAME",
                  "",
                  genquery.AS_LIST, ctx))
    return [r[0] for r in result]
