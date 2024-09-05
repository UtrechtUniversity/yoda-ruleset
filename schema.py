# -*- coding: utf-8 -*-
"""Functions for finding the active schema."""

__copyright__ = 'Copyright (c) 2018-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

import genquery

import meta
from util import *

__all__ = ['api_schema_get_schemas']


@api.make()
def api_schema_get_schemas(ctx):
    """Retrieve selectable schemas and default schema.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dit with schemas and default schema.
    """
    schemas = []

    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '/{}/yoda/schemas' AND META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = 'True'".format(user.zone(ctx), constants.SCHEMA_USER_SELECTABLE),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        schema = row[0].split('/')[-1]
        schemas.append(schema)

    if not config.default_yoda_schema:
        schema_default = ''
    else:
        schema_default = config.default_yoda_schema

    return {'schemas': schemas,
            'schema_default': schema_default}


def get_schema_collection(ctx, rods_zone, group_name):
    """Determine schema collection based upon rods zone and name of the group.

    If there is no schema id set on group level and
    the category does not have a schema, 'default' is returned.

    :param ctx:        Combined type of a callback and rei struct
    :param rods_zone:  Rods zone name
    :param group_name: Group name

    :returns: string -- Category
    """
    schema_id = get_schema_id_from_group(ctx, group_name)
    if schema_id is not None:
        return schema_id

    # Find out category based on current group_name.
    category = '-1'
    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + group_name + "' AND  META_USER_ATTR_NAME like 'category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        category = row[1]

    if category != '-1':
        # Test whether found category actually has a metadata JSON.
        # If not, fall back to default schema collection.
        # /tempZone/yoda/schemas/default/metadata.json
        schema_path = '/' + rods_zone + '/yoda/schemas/' + category

        iter = genquery.row_iterator(
            "COLL_NAME",
            "DATA_NAME like 'metadata.json' AND COLL_NAME = '" + schema_path + "'",
            genquery.AS_LIST, ctx
        )

        for _row in iter:
            return category

    return config.default_yoda_schema


def get_schema_id_from_group(ctx, group_name):
    """Returns the schema_id value that has been set on an iRODS group

    :param ctx:        Combined type of a callback and rei struct
    :param group_name: Group name

    :returns:          Schema ID, or None if none is set.
    """
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_NAME = '{}' AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'schema_id'".format(group_name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_active_schema_path(ctx, path):
    """Get the iRODS path to a schema file from a deposit, research or vault path.

    The schema collection is determined from group name of the path.

    :param ctx:   Combined type of a callback and rei struct
    :param path:  A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                  (anything after the group name is ignored)

    :returns: string -- Schema path (e.g. /tempZone/yoda/schemas/.../metadata.json)
    """
    path_parts = path.split('/')
    rods_zone  = path_parts[1]
    group_name = path_parts[3]

    # Metadata is updated in the vault, metadata is temporary stored in datamanager group.
    # e.g. /tempZone/home/datamanager-bla/vault-bla/pkg1[1667478959]/yoda-metadata.json
    if group_name.startswith("datamanager-"):
        group_name = path_parts[4]

    if group_name.startswith("vault-"):
        schema_coll = get_schema_id_from_group(ctx, group_name)
        if schema_coll is None:
            deposit_group_name = group_name.replace("vault-", "deposit-", 1)
            research_group_name = group_name.replace("vault-", "research-", 1)
            if group.exists(ctx, deposit_group_name):
                effective_group_name = deposit_group_name
            else:
                effective_group_name = research_group_name
            schema_coll = get_schema_collection(ctx, rods_zone, effective_group_name)
    else:
        schema_coll = get_schema_collection(ctx, rods_zone, group_name)

    return '/{}/yoda/schemas/{}/metadata.json'.format(rods_zone, schema_coll)


def get_active_schema(ctx, path):
    """Get a schema object from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: Schema object (parsed from JSON)
    """
    return jsonutil.read(ctx, get_active_schema_path(ctx, path))


def get_active_schema_uischema(ctx, path):
    """Get a schema and uischema object from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: Schema and UI schema object (parsed from JSON)
    """
    schema_path   = get_active_schema_path(ctx, path)
    uischema_path = '{}/{}'.format(pathutil.chop(schema_path)[0], 'uischema.json')

    return jsonutil.read(ctx, schema_path), \
        jsonutil.read(ctx, uischema_path)


def get_active_schema_id(ctx, path):
    """Get the active schema id from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: string -- Schema $id (e.g. https://yoda.uu.nl/schemas/.../metadata.json)
    """
    return get_active_schema(ctx, path)['$id']


def get_schema_id(ctx, metadata_path, metadata=None):
    """Get the current schema id from a path to a metadata json."""
    if metadata is None:
        metadata = jsonutil.read(ctx, metadata_path)
    return meta.metadata_get_schema_id(metadata)


def get_schema_path_by_id(ctx, path, schema_id):
    """Get a schema path from a schema id."""
    _, zone, _2, _3 = pathutil.info(path)

    # We do not fetch schemas from external sources, so for now assume that we
    # can find it using this pattern.
    m = re.match(r'https://yoda.uu.nl/schemas/([^/]+)/metadata.json', schema_id)
    if m:
        return '/{}/yoda/schemas/{}/metadata.json'.format(zone, m.group(1))
    else:
        return None


def get_schema_by_id(ctx, path, schema_id):
    """
    Get a schema from a schema id.

    The path is used solely to get the zone name.

    :param ctx:       Combined type of a callback and rei struct
    :param path:      A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                      (anything after the group name is ignored)
    :param schema_id: Identifier of schema to get

    :returns: Schema object (parsed from JSON)
    """
    path = get_schema_path_by_id(ctx, path, schema_id)
    if path is None:
        return None
    return jsonutil.read(ctx, path)
