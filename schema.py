# -*- coding: utf-8 -*-
"""Functions for finding the active schema."""

__copyright__ = 'Copyright (c) 2018-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

import genquery

import meta
from util import *

__all__ = []


def get_group_category(callback, rods_zone, group_name):
    """Determine category (for schema purposes) based upon rods zone and name of the group.

    If the category does not have a schema, 'default' is returned.

    :param callback:   Combined type of a callback and rei struct
    :param rods_zone:  Rods zone name
    :param group_name: Group name

    :returns: string -- Category
    """
    category = '-1'
    schemaCategory = 'default'

    # Find out where a schema_id has been set on group level
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_NAME = '{}' AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'schema_id'".format(group_name),
        genquery.AS_LIST, callback
    )

    for row in iter:
        # return found schemaCategory directly on group level
        # No further test is required here as the value found here was selected from /rodszone/yoda/schemas/ and therefore MUST be present
        log.write(callback, "FOund GROUP level schema_id: " + row[0])
        return row[0]


    # Find out category based on current group_name.
    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + group_name + "' AND  META_USER_ATTR_NAME like 'category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        category = row[1]

    if category != '-1':
        # Test whether found category actually has a metadata JSON.
        # If not, fall back to default schema collection.
        # /tempZone/yoda/schemas/default/metadata.json
        schemaCollectionName = '/' + rods_zone + '/yoda/schemas/' + category

        iter = genquery.row_iterator(
            "COLL_NAME",
            "DATA_NAME like 'metadata.json' AND COLL_NAME = '" + schemaCollectionName + "'",
            genquery.AS_LIST, callback
        )

        for _row in iter:
            schemaCategory = category    # As collection is present, the schemaCategory can be assigned the category

    log.write(callback, "FOund CATEGORY level schema_id: " + schemaCategory)
    return schemaCategory


def get_active_schema_path(callback, path):
    """Get the iRODS path to a schema file from a deposit, research or vault path.

    The schema path is determined from the category name of the path's group level.

    :param callback: Combined type of a callback and rei struct
    :param path:     A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                     (anything after the group name is ignored)

    :returns: string -- Schema path (e.g. /tempZone/yoda/schemas/.../metadata.json)
    """
    path_parts = path.split('/')
    rods_zone  = path_parts[1]
    group_name = path_parts[3]

    if group_name.startswith("vault-"):
        temp_group_name = group_name.replace("vault-", "deposit-", 1)
        if group.exists(callback, temp_group_name):
            group_name = temp_group_name
        else:
            group_name = group_name.replace("vault-", "research-", 1)

    category = get_group_category(callback, rods_zone, group_name)

    return '/{}/yoda/schemas/{}/metadata.json'.format(rods_zone, category)


def get_active_schema(callback, path):
    """Get a schema object from a research or vault path.

    :param callback: Combined type of a callback and rei struct
    :param path:     A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                     (anything after the group name is ignored)

    :returns: Schema object (parsed from JSON)
    """
    return jsonutil.read(callback, get_active_schema_path(callback, path))


def get_active_schema_uischema(callback, path):
    """Get a schema and uischema object from a research or vault path."""
    schema_path   = get_active_schema_path(callback, path)
    uischema_path = '{}/{}'.format(pathutil.chop(schema_path)[0], 'uischema.json')

    return jsonutil.read(callback, schema_path), \
        jsonutil.read(callback, uischema_path)


def get_active_schema_id(callback, path):
    """Get the active schema id from a research or vault path.

    :param callback: Combined type of a callback and rei struct
    :param path:     A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                     (anything after the group name is ignored)

    :returns: string -- Schema $id (e.g. https://yoda.uu.nl/schemas/.../metadata.json)
    """
    return get_active_schema(callback, path)['$id']


def get_schema_id(callback, metadata_path, metadata=None):
    """Get the current schema id from a path to a metadata json."""
    if metadata is None:
        metadata = jsonutil.read(callback, metadata_path)
    return meta.metadata_get_schema_id(metadata)


def get_schema_path_by_id(callback, path, schema_id):
    """Get a schema path from a schema id."""
    _, zone, _2, _3 = pathutil.info(path)

    # We do not fetch schemas from external sources, so for now assume that we
    # can find it using this pattern.
    m = re.match(r'https://yoda.uu.nl/schemas/([^/]+)/metadata.json', schema_id)
    if m:
        return '/{}/yoda/schemas/{}/metadata.json'.format(zone, m.group(1))
    else:
        return None


def get_schema_by_id(callback, path, schema_id):
    """
    Get a schema from a schema id.

    The path is used solely to get the zone name.

    :param callback:  Combined type of a callback and rei struct
    :param path:      A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                      (anything after the group name is ignored)
    :param schema_id: Identifier of schema to get

    :returns: Schema object (parsed from JSON)
    """
    path = get_schema_path_by_id(callback, path, schema_id)
    if path is None:
        return None
    return jsonutil.read(callback, path)
