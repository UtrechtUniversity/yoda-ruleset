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


def setJsonSchemaToObj(rule_args, callback, rei):
    """
    This rule stores a given JSON-schema as AVU's to an object
    :param rule_args:
        Argument 0: The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
        Argument 1: The object type
                        -d for data object
                        -R for resource
                        -C for collection
                        -u for user
        Argument 2: URL to the JSON-Schema example https://api.myjson.com/bins/17vejk
        Argument 3: The JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
    :param callback:
    :param rei:
    :return:
    """
    object_name = rule_args[0]
    object_type = rule_args[1]
    json_schema_url = rule_args[2]
    json_root = rule_args[3]

    # Check if this root has been used before
    fields = getFieldsForType(callback, object_type, object_name)
    avus = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # Regular expression pattern for unit field
    pattern = re.compile(jsonavu.RE_UNIT)

    for avu in avus:
        # Match unit to extract all info
        unit = str(avu[fields['u']])

        # If unit is matching
        if pattern.match(unit) and unit.startswith(json_root + "_"):
            callback.msiExit("-1101000", "JSON root " + json_root + " is already in use")

    # Delete existing $id AVU for this JSON root
    callback.msi_rmw_avu(object_type, object_name, '$id', "%", json_root)

    # Set new $id AVU
    callback.msi_add_avu(object_type, object_name, '$id', json_schema_url, json_root)


def getJsonSchemaFromObject(rule_args, callback, rei):
    """
    This rule get the json formatted Schema AVUs
    :param rule_args:
        Argument 0: The object name (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
        Argument 1: The object type
                        -d for data object
                        -R for resource
                        -C for collection
                        -u for user
        Argument 2: The JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
        Argument 3: The JSON-schema or "false" when no schema is set
    :param callback:
    :param rei:
    :return: JSON-schema or "false". Also set in rule_args[3]
    """
    object_name = rule_args[0]
    object_type = rule_args[1]
    json_root = rule_args[2]

    # Find AVU with a = '$id', and u = json_root. Their value is the JSON-schema URL
    fields = getFieldsForType(callback, object_type, object_name)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id' AND %s = '%s'" % (fields['a'], fields['u'], json_root)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # We're only expecting one row to be returned if any
    json_schema_url = None
    for row in rows:
        json_schema_url = row[fields['v']]

    # If no JSON-schema is known, the object is not under validation for this JSON-root
    if json_schema_url is None:
        rule_args[3] = "false"
        return "false"

    # Fetch the schema from
    schema = ""
    if json_schema_url.startswith("i:"):
        # Schema is stored as an iRODS file
        json_schema_url_irods = json_schema_url[2:]
        schema = getJsonSchemaFromiRODSObject(json_schema_url_irods, callback)

    elif json_schema_url.startswith("http://") or json_schema_url.startswith("https://"):
        # Schema is stored as an web object

        # Use requests-cache to prevent fetching the JSON-schema too often
        requests_cache.install_cache('/tmp/irods_avu_json-ruleset-cache', backend='sqlite', expire_after=60 * 60 * 24)

        try:
            r = requests.get(json_schema_url)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            callback.msiExit("-1101000", "JSON schema could not be downloaded : " + str(e.message))
            return
        schema = r.text
    else:
        # Schema is stored as an unknown object
        callback.msiExit("-1101000", "Unknown protocol or method for retrieving the JSON-schema")

    rule_args[3] = schema

    return schema


def getJsonSchemaFromiRODSObject(path, callback):
    """
        This rule gets a JSON schema stored as an iRODS object
        :param path: Full path of the json file (/nlmumc/home/rods/weight.json)
        :param callback:
        :return: JSON formatted schema
        """

    ret_val = callback.msiGetObjType(path, "")
    type_file = ret_val['arguments'][1]

    if type_file != '-d':
        callback.msiExit("-1101000", "Only files in iRODS can be used for JSON storage")
        return

    # Open iRODS file
    ret_val = callback.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val['arguments'][1]

    # Read iRODS file
    ret_val = callback.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val['arguments'][2]

    # Convert BytesBuffer to string
    ret_val = callback.msiBytesBufToStr(read_buf, "")
    output_json = ret_val['arguments'][1]

    # Close iRODS file
    callback.msiDataObjClose(file_desc, 0)

return output_json
