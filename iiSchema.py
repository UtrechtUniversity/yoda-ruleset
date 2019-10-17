# \file      iiSchema.py
# \brief     Functions for finding the active schema.
# \author    Lazlo Westerhof
# \author    Felix Croes
# \author    Harm de Raaff
# \author    Chris Smeele
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


def get_group_category(callback, rods_zone, group_name):
    """Determine category (for schema purposes) based upon rods zone and name of the group.
       If the category does not have a schema, 'default' is returned.

       Arguments:
       rods_zone  -- Rods zone name
       group_name -- Group name

       Return:
       string -- Category
    """
    category = '-1'
    schemaCategory = 'default'

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

        for row in iter:
            schemaCategory = category    # As collection is present, the schemaCategory can be assigned the category

    return schemaCategory


def get_active_schema_path(callback, path):
    """Get the iRODS path to a schema file from a research or vault path.
       The schema path is determined from the category name of the path's group level.

       Arguments:
       path -- A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
              (anything after the group name is ignored)

       Return:
       Schema path (e.g. /tempZone/yoda/schemas/.../metadata.json)
    """
    path_parts = path.split('/')
    rods_zone  = path_parts[1]
    group_name = path_parts[3]

    if group_name.startswith("vault-"):
        group_name = group_name.replace("vault-", "research-", 1)

    category = get_group_category(callback, rods_zone, group_name)

    return '/{}/yoda/schemas/{}/metadata.json'.format(rods_zone, category)


def get_active_schema(callback, path):
    """Get a schema object from a research or vault path.

       Arguments:
       path -- A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
              (anything after the group name is ignored)

       Return:
       Schema object (parsed from JSON)
    """
    return read_json_object(callback, get_active_schema_path(callback, path))


def get_active_schema_uischema(callback, path):
    """Get a schema and uischema object from a research or vault path."""

    schema_path   = get_active_schema_path(callback, path)
    uischema_path = '{}/{}'.format(chop_path(schema_path)[0], 'uischema.json')

    return read_json_object(callback, schema_path), \
        read_json_object(callback, uischema_path)


def get_active_schema_id(callback, path):
    """Get the active schema id from a research or vault path.

       Arguments:
       path -- A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
              (anything after the group name is ignored)

       Return:
       string -- Schema $id (e.g. https://yoda.uu.nl/schemas/.../metadata.json)
    """

    return get_active_schema(callback, path)['$id']


def get_schema_id(callback, metadata_path, metadata=None):
    """Get the current schema id from a path to a metadata json."""
    if metadata is None:
        metadata = read_json_object(callback, metadata_path)
    return metadata_get_schema_id(metadata)


def get_schema_path_by_id(callback, path, schema_id):
    """Get a schema path from a schema id."""

    _, zone, _2, _3 = get_path_info(path)

    # We do not fetch schemas from external sources, so for now assume that we
    # can find it using this pattern.
    m = re.match(r'https://yoda.uu.nl/schemas/([^/]+)/metadata.json', schema_id)
    if m:
        return '/{}/yoda/schemas/{}/metadata.json'.format(zone, m.group(1))
    else:
        return None


def get_schema_by_id(callback, path, schema_id):
    """The path is used solely to get the zone name"""
    path = get_schema_path_by_id(callback, path, schema_id)
    if path is None:
        return None
    return read_json_object(callback, path)
