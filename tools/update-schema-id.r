#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Update the schema id for each group based on collection schema
# 
# Example command to run:
# irule -r irods_rule_engine_plugin-python-instance -F tools/update-schema-id.r '*defaultSchema="'default-3'"'
import genquery
import session_vars

def get_schema_collection(ctx, rods_zone, group_name, default_schema):
    """Determine schema collection based upon rods zone and name of the group.
    (shamelessly copied from schema.py, then tweaked)

    If there is no schema id set on group level and
    the category does not have a schema, 'default' is returned.

    :param ctx:            Combined type of a callback and rei struct
    :param rods_zone:      Rods zone name
    :param group_name:     Group name
    :param default_schema: Default schema if no schema found

    :returns: string -- Category
    """
    # Find out whether a schema_id has been set on group level.
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_NAME = '{}' AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'schema_id'".format(group_name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # Return schema id if found on group level.
        # No further test is required here as the value found here was selected
        # from /rods_zone/yoda/schemas/ and therefore must be present.
        return row[0]

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
        schema_coll = default_schema

        iter = genquery.row_iterator(
            "COLL_NAME",
            "DATA_NAME like 'metadata.json' AND COLL_NAME = '" + schema_path + "'",
            genquery.AS_LIST, ctx
        )

        for _row in iter:
            schema_coll = category  # As collection is present, the schema_collection can be assigned the category.

    return schema_coll


def main(rule_args, callback, rei):
    zone = session_vars.get_map(rei)['client_user']['irods_zone']
    userList = []

    default_schema = global_vars["*defaultSchema"][1:-1]

    # Get the group names
    userIter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_ZONE = '{}'".format(zone),
        genquery.AS_LIST,
        callback) 

    for row in userIter:
        name = row[0]
        # Normalish groups
        if name.startswith("research-") or name.startswith("deposit-") or name.startswith("grp-") or name.startswith("intake-"):
            metaIter = genquery.row_iterator(
                "META_USER_ATTR_NAME",
                "USER_GROUP_NAME = '{}' AND USER_ZONE = '{}'".format(name, zone),
                genquery.AS_LIST,
                callback)
            schemaIdFound = False
            for row1 in metaIter:
                attr = row1[0]
                if attr == 'schema_id':
                    schemaIdFound = True
            
            if not schemaIdFound:
                schema_collection = get_schema_collection(callback, zone, name, default_schema)
                callback.uuGroupModify(name, 'schema_id', schema_collection, '', '') 
                callback.writeLine("stdout", "Group {} set with schema id {}".format(name, schema_collection))


INPUT *defaultSchema=""
OUTPUT ruleExecOut
