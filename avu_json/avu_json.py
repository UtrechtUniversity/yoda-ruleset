# -*- coding: utf-8 -*-
"""Bidirectional conversion between JSON(-LD) and iRODS AVUs."""

__copyright__ = ['Copyright (c) 2019, Maastricht University',
                 'Copyright (c) 2020, Utrecht University']
__license__   = 'Apache License 2.0, see LICENSE'

import json

import genquery
import irods_types
import jsonavu
import jsonschema
import requests
import requests_cache


# Global vars
activelyUpdatingAVUs = False


def set_json_to_obj(ctx, object_name, object_type, json_namespace, json_string):
    """This rule stores a given json string as AVU's to an object.

    :param ctx:            iRODS context
    :param object_name:    The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
    :param object_type:    The object type
                             -d for data object
                             -R for resource
                             -C for collection
                             -u for user
    :param json_namespace: The JSON namespace according to https://github.com/MaastrichtUniversity/irods_avu_json.
    :param json_string:    The JSON string {"k1":"v1","k2":{"k3":"v2","k4":"v3"},"k5":["v4","v5"],"k6":[{"k7":"v6","k8":"v7"}]}
    """
    try:
        data = json.loads(json_string)
    except ValueError:
        ctx.msiExit("-1101000", "Invalid JSON provided")
        return

    # Retrieve a JSON-schema if any is set
    schema = get_json_schema_from_object(ctx, object_name, object_type, json_namespace)

    # Perform validation if required
    if schema:
        try:
            schema = json.loads(schema)
        except ValueError:
            ctx.msiExit("-1101000", "Invalid JSON-schema provided")
            return

        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            ctx.msiExit("-1101000", "JSON instance could not be validated against JSON-schema: " + str(e))
            return

    # Load global variable activelyUpdatingAVUs and set this to true. At this point we are actively updating
    # AVUs and want to disable the check for not being able to set JSON AVUs directly
    global activelyUpdatingAVUs
    activelyUpdatingAVUs = True

    ret_val = ctx.msi_rmw_avu(object_type, object_name, "%", "%", json_namespace + "_%")
    if ret_val['status'] is False and ret_val['code'] != -819000:
        return

    avu = jsonavu.json2avu(data, json_namespace)

    for i in avu:
        ctx.msi_add_avu(object_type, object_name, i["a"], i["v"], i["u"])

    # Set global variable activelyUpdatingAVUs to false. At this point we are done updating AVU and want
    # to enable some of the checks.
    activelyUpdatingAVUs = False


def get_fields_for_type(ctx, object_type, object_name):
    """Helper function to convert iRODS object type to the corresponding field names in GenQuery.

    :param ctx:         iRODS context
    :param object_type: The object type
                          -d for data object
                          -R for resource
                          -C for collection
                          -u for user
    :param object_name: The object (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)

    :return: an dictionary with the field names set in a, v, u and a WHERE clausal
    """
    fields = dict()

    if object_type.lower() == '-d':
        fields['a'] = "META_DATA_ATTR_NAME"
        fields['v'] = "META_DATA_ATTR_VALUE"
        fields['u'] = "META_DATA_ATTR_UNITS"

        # For a data object the path needs to be split in the object and collection
        ret_val = ctx.msiSplitPath(object_name, "", "")
        object_name = ret_val['arguments'][2]
        collection = ret_val['arguments'][1]

        fields['WHERE'] = "COLL_NAME = '" + collection + "' AND DATA_NAME = '" + object_name + "'"

    elif object_type.lower() == '-c':
        fields['a'] = "META_COLL_ATTR_NAME"
        fields['v'] = "META_COLL_ATTR_VALUE"
        fields['u'] = "META_COLL_ATTR_UNITS"

        fields['WHERE'] = "COLL_NAME = '" + object_name + "'"

    elif object_type.lower() == '-r':
        fields['a'] = "META_RESC_ATTR_NAME"
        fields['v'] = "META_RESC_ATTR_VALUE"
        fields['u'] = "META_RESC_ATTR_UNITS"

        fields['WHERE'] = "RESC_NAME = '" + object_name + "'"

    elif object_type.lower() == '-u':
        fields['a'] = "META_USER_ATTR_NAME"
        fields['v'] = "META_USER_ATTR_VALUE"
        fields['u'] = "META_USER_ATTR_UNITS"

        fields['WHERE'] = "USER_NAME = '" + object_name + "'"
    else:
        ctx.msiExit("-1101000", "Object type should be -d, -C, -R or -u")

    return fields


def get_json_schema_from_object(ctx, object_name, object_type, json_namespace):
    """This rule get the JSON formatted Schema AVUs.

    :param ctx:            iRODS context
    :param object_name:    The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
    :param object_type:    The object type
                             -d for data object
                             -R for resource
                             -C for collection
                             -u for user
    :param json_namespace: The JSON namespace according to https://github.com/MaastrichtUniversity/irods_avu_json.

    :return: The JSON-schema or "False" when no schema is set.
    """
    # Find AVU with a = '$id', and u = json_namespace. Their value is the JSON-schema URL
    fields = get_fields_for_type(ctx, object_type, object_name)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id' AND %s = '%s'" % (fields['a'], fields['u'], json_namespace)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, ctx)

    # We're only expecting one row to be returned if any
    json_schema_url = None
    for row in rows:
        json_schema_url = row[fields['v']]

    # If no JSON-schema is known, the object is not under validation for this JSON-namespace
    if json_schema_url is None:
        return False

    # Fetch the schema from
    schema = ""
    if json_schema_url.startswith("i:"):
        # Schema is stored as an iRODS file
        json_schema_url_irods = json_schema_url[2:]
        schema = get_json_schema_from_irods_object(ctx, json_schema_url_irods)

    elif json_schema_url.startswith("http://") or json_schema_url.startswith("https://"):
        # Schema is stored as an web object

        # Use requests-cache to prevent fetching the JSON-schema too often
        requests_cache.install_cache('/tmp/irods_avu_json-ruleset-cache', backend='sqlite', expire_after=60 * 60 * 24)

        try:
            r = requests.get(json_schema_url, timeout=30)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            ctx.msiExit("-1101000", "JSON schema could not be downloaded : " + str(e))
            return
        schema = r.text
    else:
        # Schema is stored as an unknown object
        ctx.msiExit("-1101000", "Unknown protocol or method for retrieving the JSON-schema")

    return schema


def get_json_schema_from_irods_object(ctx, path):
    """This rule gets a JSON schema stored as an iRODS object

    :param ctx:  iRODS context
    :param path: Full path of the json file (/nlmumc/home/rods/weight.json)

    :return: JSON formatted schema
    """
    ret_val = ctx.msiGetObjType(path, "")
    type_file = ret_val['arguments'][1]

    if type_file != '-d':
        ctx.msiExit("-1101000", "Only files in iRODS can be used for JSON storage")
        return

    # Open iRODS file
    ret_val = ctx.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val['arguments'][1]

    # Read iRODS file
    ret_val = ctx.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val['arguments'][2]

    # Convert BytesBuffer to string
    ret_val = ctx.msiBytesBufToStr(read_buf, "")
    output_json = ret_val['arguments'][1]

    # Close iRODS file
    ctx.msiDataObjClose(file_desc, 0)

    return output_json
