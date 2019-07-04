# \file      uuJsonAvu.py
# \brief     Functions for setting JSON data as AVUs on an iRODS object
# \copyright Copyright (c) 2019 Maastricht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import jsonavu
import genquery
import jsonschema
import requests
import requests_cache
import irods_types
import re

# Global vars
activelyUpdatingAVUs = False


def setJsonToObj(rule_args, callback, rei):
    """
    This rule stores a given json string as AVU's to an object.
    :param rule_args:
        Argument 0: The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
        Argument 1: The object type
                        -d for data object
                        -R for resource
                        -C for collection
                        -u for user
        Argument 2:  The JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
        Argument 3:  the JSON string {"k1":"v1","k2":{"k3":"v2","k4":"v3"},"k5":["v4","v5"],"k6":[{"k7":"v6","k8":"v7"}]}
    :param callback:
    :param rei:
    :return:
    """

    object_name = rule_args[0]
    object_type = rule_args[1]
    json_root = rule_args[2]
    json_string = rule_args[3]

    try:
        data = json.loads(json_string)
    except ValueError:
        callback.msiExit("-1101000", "Invalid JSON provided")
        return

    # Retrieve a JSON-schema if any is set
    ret_val = callback.getJsonSchemaFromObject(object_name, object_type, json_root, "")
    schema = ret_val['arguments'][3]

    # Perform validation if required
    if schema != "false":
        try:
            schema = json.loads(schema)
        except ValueError:
            callback.msiExit("-1101000", "Invalid JSON-schema provided")
            return

        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError, e:
            callback.msiExit("-1101000", "JSON instance could not be validated against JSON-schema: " + str(e.message))
            return

    # Load global variable activelyUpdatingAVUs and set this to true. At this point we are actively updating
    # AVUs and want to disable the check for not being able to set JSON AVUs directly
    global activelyUpdatingAVUs
    activelyUpdatingAVUs = True

    ret_val = callback.msi_rmw_avu(object_type, object_name, "%", "%", json_root + "_%")
    if ret_val['status'] is False and ret_val['code'] != -819000:
        return

    avu = jsonavu.json2avu(data, json_root)

    for i in avu:
        callback.msi_add_avu(object_type, object_name, i["a"], i["v"], i["u"])

    # Set global variable activelyUpdatingAVUs to false. At this point we are done updating AVU and want
    # to enable some of the checks.
    activelyUpdatingAVUs = False


def getJsonFromObj(rule_args, callback, rei):
    """
    This function return a JSON string from AVU's set to an object
    :param rule_args:
        Argument 0: The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
        Argument 1: The object type
                        -d for data object
                        -R for resource
                        -C for collection
                        -u for user
        Argument 2: The JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
        Argument 3: The JSON string
    :param callback:
    :param rei:
    :return: JSON string is returned in rule_args[3]
    """
    object_name = rule_args[0]
    object_type = rule_args[1]
    json_root = rule_args[2]

    # Get all AVUs
    fields = getFieldsForType(callback, object_type, object_name)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    avus = []
    for row in rows:
        avus.append({
            "a": row[fields['a']],
            "v": row[fields['v']],
            "u": row[fields['u']]
        })

    # Convert AVUs to JSON
    parsed_data = jsonavu.avu2json(avus, json_root)
    result = json.dumps(parsed_data)

    rule_args[3] = result


def getFieldsForType(callback, object_type, object_name):
    """
    Helper function to convert iRODS object type to the corresponding field names in GenQuery
    :param callback:
    :param object_type: The object type
                        -d for data object
                        -R for resource
                        -C for collection
                        -u for user
    :param object_name:  The object (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
    :return: an dictionary with the field names set in a, v, u and a WHERE clausal
    """
    fields = dict()

    if object_type.lower() == '-d':
        fields['a'] = "META_DATA_ATTR_NAME"
        fields['v'] = "META_DATA_ATTR_VALUE"
        fields['u'] = "META_DATA_ATTR_UNITS"

        # For a data object the path needs to be split in the object and collection
        ret_val = callback.msiSplitPath(object_name, "", "")
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
        callback.msiExit("-1101000", "Object type should be -d, -C, -R or -u")

    return fields
