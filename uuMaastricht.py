import json
import sys
import jsonavu
import session_vars
import genquery
import jsonschema
import requests
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
        callback.writeLine("serverLog", "Invalid json provided")
        callback.msiExit("-1101000", "Invalid json provided")
        return

    # check if validation is required
    validation_required = False
    json_schema_url = ""

    # Find AVUs with a = '$id', and u = json_root. Their value is the JSON-schema URL
    fields = getFieldsForType(callback, object_type, object_name)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id' AND %s = '%s'" % (fields['a'], fields['u'], json_root)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # We're only expecting one row to be returned if any
    for row in rows:
        validation_required = True
        json_schema_url = row[fields['v']]

    if validation_required:
        # TODO: This needs to accept more types of URLs
        try:
            r = requests.get(json_schema_url)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            callback.writeLine("serverLog",
                               "JSON schema could not be downloaded :" + str(e.message))
            callback.msiExit("-1101000", "JSON schema could not be downloaded : " + str(e.message))
            return

        schema = r.json()
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError, e:
            callback.writeLine("serverLog",
                               "JSON Instance could not be validated against JSON-schema " + str(e.message))
            callback.msiExit("-1101000", "JSON Instance could not be validated against JSON-schema : " + str(e.message))
            return

    # Load global variable activelyUpdatingAVUs and set this to true. At this point we are actively updating
    # AVUs and want to disable the check for not being able to set JSON AVUs directly
    global activelyUpdatingAVUs
    activelyUpdatingAVUs = True

    ret_val = callback.msi_rmw_avu(object_type, object_name, "%", "%", json_root + "_%")
    if ret_val['status'] is False and ret_val['code'] != -819000:
        callback.writeLine("serverLog", "msi_rmw_avu failed with: " + ret_val['code'])
        return

    avu = jsonavu.json2avu(data, json_root)

    for i in avu:
        callback.msi_add_avu(object_type, object_name, i["a"], i["v"], i["u"])

    # Set global variable activelyUpdatingAVUsthis to false. At this point we are done updating AVU and want
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
        Argument 3: The
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
        callback.writeLine("serverLog", "Object type should be -d, -C, -R or -u")
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
            callback.writeLine("serverLog", "JSON root " + json_root + " is already in use")
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
    :param callback:
    :param rei:
    :return: json formatted Schema AVUs
    """

    object_name = rule_args[0]
    object_type = rule_args[1]

    # Get all AVUs with attribute $id
    fields = getFieldsForType(callback, object_type, object_name)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id'" % (fields['a'])
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    avus = []
    for row in rows:
        avus.append({
            "a": row[fields['a']],
            "v": row[fields['v']],
            "u": row[fields['u']]
        })

    result = json.dumps(avus)

    rule_args[2] = result


def allowAvuChange(object_name, object_type, unit, callback):
    """
    This function checks if an AVU change should be allowed. If the unit is part of an existing JSON changing should
    not be allowed. Unless the change is done from setJsonToObj()
    :param object_name: The object (/nlmumc/P000000003, /nlmumc/projects/metadata.xml, user@mail.com, demoResc)
    :param object_type:
            The object type
                -d for data object
                -R for resource
                -C for collection
                -u for user
    :param unit: The unit to check for
    :param callback:
    :return: boolean
    """
    global activelyUpdatingAVUs
    # Check if we are activelyUpdatingAVUs from setJsonToObj. In that case we do not want the filtering below
    if activelyUpdatingAVUs:
        return True

    # Get all AVUs with attribute $id
    fields = getFieldsForType(callback, object_type, object_name)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id'" % (fields['a'])
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # From these AVUs extract the unit (root)
    root_list = []
    for row in rows:
        root_list.append(row[fields['u']])

    # Get the unit from the avu that is currently added.
    for root in root_list:
        # If the unit start with one of the roots, disallow the operation
        if str(unit).startswith(root + "_"):
            return False

    return True


def pep_database_set_avu_metadata_pre(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_set_avu_metadata_pre. Arguments: " + str(len(rule_args)))

    object_name = rule_args[4]
    object_type = rule_args[3]
    object_unit = rule_args[7]
    object_attribute = rule_args[5]

    # This policy is not using the helper allowAvuChange function as the set operation can also modify units indirectly

    # Get all AVUs with attribute $id
    fields = getFieldsForType(callback, object_type, object_name)
    fields_id = fields['WHERE'] + " AND %s = '$id'" % (fields['a'])
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields_id, genquery.AS_DICT, callback)

    # From these AVUs extract the unit (root)
    root_list = []
    for row in rows:
        root_list.append(row[fields['u']])

    # Get the unit from the avu that is currently added.
    for root in root_list:
        # If the unit start with one of the roots, disallow the operation
        if str(object_unit).startswith(root + "_"):
            callback.msiOprDisallowed()

    # A set operation can also change the unit of existing attributes
    fields_a = fields['WHERE'] + " AND %s = '%s'" % (fields['a'], object_attribute)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields_a, genquery.AS_DICT, callback)

    for row in rows:
        for root in root_list:
            # If the unit start with one of the roots, disallow the operation
            if str(row[fields['u']]).startswith(root + "_"):
                callback.msiOprDisallowed()


# TODO pep_database_add_avu_metadata_wild_pre does not work for wildcards
def pep_database_add_avu_metadata_wild_pre(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_add_avu_metadata_wild_pre. Arguments: " + str(len(rule_args)))
    # for i in range(len(rule_args)):
    #    callback.writeLine("serverLog", "Argument " + str(i) + "is " + str(rule_args[i]))

    object_name = rule_args[5]
    object_type = rule_args[4]
    object_unit = rule_args[8]

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_add_avu_metadata_pre(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_add_avu_metadata_pre. Arguments: " + str(len(rule_args)))

    object_name = rule_args[5]
    object_type = rule_args[4]
    object_unit = rule_args[8]

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_mod_avu_metadata_prep(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_mod_avu_metadata_prep. Arguments: " + str(len(rule_args)))

    object_name = rule_args[4]
    object_type = rule_args[3]
    object_old_unit = rule_args[7]
    object_new_unit = rule_args[10]

    # If old unit starts with one of the roots disallow
    if not allowAvuChange(object_name, object_type, object_old_unit, callback):
        callback.msiOprDisallowed()

    # If new unit starts with one of the roots disallow
    if not allowAvuChange(object_name, object_type, object_new_unit, callback):
        callback.msiOprDisallowed()


def pep_database_del_avu_metadata_pre(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_del_avu_metadata_pre. Arguments: " + str(len(rule_args)))
    object_name = rule_args[5]
    object_type = rule_args[4]
    object_attribute = rule_args[6]
    object_value = rule_args[7]
    object_unit = rule_args[8]

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()

    # Wild card removal check
    if "%" in [object_attribute, object_value, object_unit]:
        # Get all AVU for the from object
        fields = getFieldsForType(callback, object_type, object_name)
        fields_a = fields['WHERE']
        # if a,v or u is not wild card add to filter
        if object_attribute != "%":
            fields_a = fields_a + " AND %s = '%s'" % (fields['a'], object_attribute)
        if object_value != "%":
            fields_a = fields_a + " AND %s = '%s'" % (fields['v'], object_value)
        if object_unit != "%":
            fields_a = fields_a + " AND %s = '%s'" % (fields['u'], object_unit)
        avus = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields_a,
                                     genquery.AS_DICT, callback)
        for avu in avus:
            unit = str(avu[fields['u']])
            if not allowAvuChange(object_name, object_type, unit, callback):
                callback.msiOprDisallowed()


def pep_database_copy_avu_metadata_pre(rule_args, callback, rei):
    # callback.writeLine("serverLog", "pep_database_copy_avu_metadata_pre. Arguments: " + str(len(rule_args)))

    object_name_from = rule_args[5]
    object_type_from = rule_args[3]
    object_name_to = rule_args[6]
    object_type_to = rule_args[4]

    # Get all AVU for the from object
    fields_from = getFieldsForType(callback, object_type_from, object_name_from)
    avus_from = genquery.row_iterator([fields_from['a'], fields_from['v'], fields_from['u']], fields_from['WHERE'],
                                      genquery.AS_DICT, callback)

    # Get all AVUs with attribute $id from the to object
    fields_to = getFieldsForType(callback, object_type_to, object_name_to)
    fields_id = fields_to['WHERE'] + " AND %s = '$id'" % (fields_to['a'])
    rows = genquery.row_iterator([fields_to['a'], fields_to['v'], fields_to['u']], fields_id, genquery.AS_DICT,
                                 callback)

    # From these AVUs extract the unit (root)
    root_list_to = []
    for row in rows:
        root_list_to.append(row[fields_to['u']])

    # Regular expression pattern for unit field
    pattern = re.compile(jsonavu.RE_UNIT)

    # For all AVUs on the from object check if one starts with the one of the root from the to object
    for avu in avus_from:
        for root in root_list_to:
            # Match unit to extract all info
            unit = str(avu[fields_from['u']])

            # If unit is matching
            if pattern.match(unit) and unit.startswith(root + "_"):
                # callback.writeLine("serverLog", "JSON root " + root + " is already in use in the to object")
                # callback.msiExit("-1101000", "JSON root " + root + " is already in use in the to object")
                callback.msiOprDisallowed()

# TODO: Do more copy cases need to be covered?
