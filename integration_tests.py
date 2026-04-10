"""Integration tests for the development environment."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_run_integration_tests']

import json
import os
import re
import subprocess
import time
import traceback
import uuid
from subprocess import PIPE, Popen
from typing import List

import genquery

import data_access_token
import folder
import groups
import meta
import research
import schema
from stats import get_resource_monthly_category_stats, get_user_groups_for_stats
from util import api, avu, collection, config, constants, data_object, diff_data, group, jsonutil, log, measure_coverage, msi, resources, rule, user
from vault import copy_acls_from_parent, copy_folder_to_research


def _call_msvc_stat_vault(ctx, resc_name, data_path):
    if config.enable_nfs_resource:
        data_path = data_path.replace("/var/lib/irods/", "/nfs/")
    ret = msi.stat_vault(ctx, resc_name, data_path, '', '')
    return (ret['arguments'][2], ret['arguments'][3])


def _call_msvc_stat_vault_check_exc(ctx, resc_name, data_path):
    """Verifies whether a call to the stat vault microservices raises an exception"""
    try:
        msi.stat_vault(ctx, resc_name, data_path, '', '')
        return False
    except Exception:
        return True


def _call_msvc_json_arrayops(ctx, jsonstr, val, ops, index, argument_index):
    """Returns an output argument from the json_arrayops microservice"""
    return ctx.msi_json_arrayops(jsonstr, val, ops, index)["arguments"][argument_index]


def _call_msvc_json_objops(ctx, jsonstr, val, ops, argument_index):
    """Returns an output argument from the json_objops microservice"""
    result = ctx.msi_json_objops(jsonstr, val, ops)["arguments"]
    if ops == "get":
        return list(result[argument_index].key), list(result[argument_index].value)
    else:
        return result[argument_index]


def _create_tmp_object(ctx):
    """Creates a randomly named test data object and returns its name"""
    path = "/{}/home/rods/{}.test".format(user.zone(ctx), str(uuid.uuid4()))
    data_object.write(ctx, path, "test")
    return path


def _create_tmp_collection(ctx):
    """Creates a randomly named test collection and returns its name"""
    path = "/{}/home/rods/{}-test".format(user.zone(ctx), str(uuid.uuid4()))
    collection.create(ctx, path)
    return path


def _test_avu_associate_to_data(ctx):
    tmp_object = _create_tmp_object(ctx)
    avu.associate_to_data(ctx, tmp_object, "foo", "bar", "baz")
    result = [(m.attr, m.value, m.unit) for m in avu.of_data(ctx, tmp_object)]
    data_object.remove(ctx, tmp_object)
    return result


def _test_avu_associate_to_coll(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    avu.associate_to_coll(ctx, tmp_coll, "foo", "bar", "baz")
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_coll)]
    collection.remove(ctx, tmp_coll)
    return result


def _test_avu_set_collection(ctx, catch):
    # Test setting avu with catch and without catch
    tmp_coll = _create_tmp_collection(ctx)
    avu.set_on_coll(ctx, tmp_coll, "foo", "bar", catch)
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_coll)]
    collection.remove(ctx, tmp_coll)
    return result


def _test_avu_rmw_collection(ctx, rmw_attributes):
    # Test removing with catch and without catch
    tmp_coll = _create_tmp_collection(ctx)
    avu.associate_to_coll(ctx, tmp_coll, "foo", "bar", "baz")
    avu.associate_to_coll(ctx, tmp_coll, "aap", "noot", "mies")
    avu.rmw_from_coll(ctx, tmp_coll, rmw_attributes[0], rmw_attributes[1], rmw_attributes[2], rmw_attributes[3])
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_coll)]
    collection.remove(ctx, tmp_coll)
    return result


def _test_avu_get_attr_val_of_coll(ctx, attr, value):
    # Test getting the value of an attribute on a collection
    tmp_coll = _create_tmp_collection(ctx)
    avu.associate_to_coll(ctx, tmp_coll, attr, value, "baz")
    result = avu.get_attr_val_of_coll(ctx, tmp_coll, attr)
    collection.remove(ctx, tmp_coll)
    return result


def _test_avu_get_attr_val_of_coll_exception(ctx):
    # Test that getting a non existing attribute on a collection raises an exception (True for exception raised)
    tmp_coll = _create_tmp_collection(ctx)
    result = False
    try:
        result = avu.get_attr_val_of_coll(ctx, tmp_coll, "foo")
    except Exception:
        result = True
    collection.remove(ctx, tmp_coll)
    return result


def _test_folder_set_retry_avus(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    folder.folder_secure_set_retry_avus(ctx, tmp_coll, 2)
    # Needed to be able to delete collection
    msi.set_acl(ctx, "default", "admin:own", user.full_name(ctx), tmp_coll)
    collection.remove(ctx, tmp_coll)
    return True


def _test_msvc_apply_atomic_operations_collection(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    operations = {
        "entity_name": tmp_coll,
        "entity_type": "collection",
        "operations": [
            {
                "operation": "add",
                "attribute": "aap",
                "value": "noot",
                "units": "mies"
            },
            {
                "operation": "add",
                "attribute": "foo",
                "value": "bar",
                "units": "baz"
            },
            {
                "operation": "remove",
                "attribute": "aap",
                "value": "noot",
                "units": "mies"
            }
        ]
    }
    avu.apply_atomic_operations(ctx, operations)
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_coll)]
    collection.remove(ctx, tmp_coll)
    return result


def _test_msvc_apply_atomic_operations_object(ctx):
    tmp_object = _create_tmp_object(ctx)
    operations = {
        "entity_name": tmp_object,
        "entity_type": "data_object",
        "operations": [
            {
                "operation": "add",
                "attribute": "aap",
                "value": "noot",
                "units": "mies"
            },
            {
                "operation": "add",
                "attribute": "foo",
                "value": "bar",
                "units": "baz"
            },
            {
                "operation": "remove",
                "attribute": "aap",
                "value": "noot",
                "units": "mies"
            }
        ]
    }
    avu.apply_atomic_operations(ctx, operations)
    result = [(m.attr, m.value, m.unit) for m in avu.of_data(ctx, tmp_object)]
    data_object.remove(ctx, tmp_object)
    return result


def _test_jsonutil_set_on_object_collection(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    jsonutil.set_on_object(ctx, tmp_coll, "collection", "root", "{\"inspector\": \"gadget\"}")
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_coll)]
    collection.remove(ctx, tmp_coll)
    return result


def _test_jsonutil_set_on_object_data_object(ctx):
    tmp_object = _create_tmp_object(ctx)
    jsonutil.set_on_object(ctx, tmp_object, "data_object", "root", "{\"inspector\": \"gadget\"}")
    result = [(m.attr, m.value, m.unit) for m in avu.of_data(ctx, tmp_object)]
    data_object.remove(ctx, tmp_object)
    return result


def _test_folder_cronjob_status(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    result_set = folder.set_cronjob_status(ctx, constants.CRONJOB_STATE['RETRY'], tmp_coll)
    status = folder.get_cronjob_status(ctx, tmp_coll)
    correct_status = status == constants.CRONJOB_STATE['RETRY']
    result_rm = folder.rm_cronjob_status(ctx, tmp_coll)
    collection.remove(ctx, tmp_coll)
    return result_set, correct_status, result_rm


def _test_folder_set_get_last_run(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    result = folder.set_last_run_time(ctx, tmp_coll)
    found, last_run = folder.get_last_run_time(ctx, tmp_coll)
    collection.remove(ctx, tmp_coll)
    return result, found, last_run


def _test_groups_data(ctx, test_group, attribute, value):
    avu.associate_to_group(ctx, test_group, attribute, value, "")
    try:
        groups_data = groups.internal_api_group_data(ctx)
    except KeyError:
        avu.rmw_from_group(ctx, test_group, attribute, value, "")
        raise

    avu.rmw_from_group(ctx, test_group, attribute, value, "")
    group_names = [group
                   for catdata in groups_data['group_hierarchy'].values()
                   for subcatdata in catdata.values()
                   for group in subcatdata]
    # We check here that the function still works if the test user has a
    # group attribute, but doesn't have all the attributes needed to be
    # a research group. Also check that data is still returned for valid
    # group manager managed groups.
    return ("research-default-3" in group_names
            and "datarequests-research-datamanagers" in group_names
            and "grp-vault-test" in group_names
            and "intake-test2" in group_names
            and "deposit-pilot" in group_names
            and "datamanager-test-automation" in group_names
            and test_group not in group_names)


def _test_statistics_exportdata(ctx: rule.Context) -> List[str]:
    """Test function to calculate statistics export data

    :param ctx:  Combined type of a callback and rei struct

    :returns: List of unexpected test results

    """
    errors: List[str] = []

    # We run a statistics update to ensure that statistics AVUs are
    # available.
    statistics_update_command = ["/bin/irule",
                                 "-r",
                                 "irods_rule_engine_plugin-irods_rule_language-instance",
                                 "-F",
                                 "/etc/irods/yoda-ruleset/tools/storage-statistics.r"]
    subprocess.run(statistics_update_command)

    # Retrieve export data
    exportdata = get_resource_monthly_category_stats(ctx)

    # Basic tests of output structure
    if "storage" not in exportdata:
        errors.append("Storage section missing")
    if "dates" not in exportdata:
        errors.append("Dates section missing")
    if "metadata" not in exportdata:
        errors.append("Metadata section missing")
    if len(errors) > 0:
        # Other tests depend on the structure of the export data
        # meeting the expected format, so it does not make sense to
        # continue if we have errors at this point.
        return errors

    # Storage tests
    storagedata = exportdata['storage']
    if len(storagedata) < 20:
        errors.append("Fewer groups in storage data than expected: " + str(len(storagedata)))

    research_initial_data = [d for d in storagedata if d['groupname'] == "research-initial"]
    if len(research_initial_data) == 0:
        errors.append("Research-initial not found in storage data")
    elif len(research_initial_data) > 1:
        errors.append("Research-initial is present multiple times in storage data")
    else:
        category = research_initial_data[0].get('category', 'category not found')
        if category != "test-automation":
            errors.append("Research-initial has unexpected category: " + category)
        subcategory = research_initial_data[0].get('subcategory', 'subcategory not found')
        if subcategory != "initial":
            errors.append("Research-initial has unexpected subcategory: " + subcategory)
        storagefigures = research_initial_data[0].get('storage')
        if len(storagefigures) == 0:
            errors.append("No storage figures found for research-initial")
        elif storagefigures[-1] < 1000000:
            errors.append("Last storage figure for research-initial is lower than expected: "
                          + str(storagefigures[-1]))

    # Dates test
    dates = exportdata['dates']
    if len(dates) == 0:
        errors.append("No dates in export data.")

    # Metadata tests
    metadata = exportdata['metadata']
    if "timestamp" not in metadata:
        errors.append("Timestamp missing in metadata")
    if "readable_timestamp" not in metadata:
        errors.append("Human-readable timestamp missing in metadata")

    return errors


def _test_schema_active_schema_deposit_from_default(ctx):
    avu.rm_from_group(ctx, "deposit-pilot", "schema_id", "dag-0")
    result = schema.get_active_schema_path(ctx, "/tempZone/home/deposit-pilot")
    avu.associate_to_group(ctx, "deposit-pilot", "schema_id", "dag-0")
    return result


def _test_schema_active_schema_research_from_default(ctx):
    avu.rm_from_group(ctx, "research-core-2", "schema_id", "core-2")
    result = schema.get_active_schema_path(ctx, "/tempZone/home/research-core-2")
    avu.associate_to_group(ctx, "research-core-2", "schema_id", "core-2")
    return result


def _test_schema_active_schema_vault_research_override(ctx):
    avu.associate_to_group(ctx, "vault-core-2", "schema_id", "integration-test-schema-1")
    result = schema.get_active_schema_path(ctx, "/tempZone/home/vault-core-2")
    avu.rm_from_group(ctx, "vault-core-2", "schema_id", "integration-test-schema-1")
    return result


def _test_schema_active_schema_vault_without_research(ctx):
    ctx.uuGroupAdd("vault-without-research", "test-automation", "something", "", "", "", "", "", "", "", "")
    result = schema.get_active_schema_path(ctx, "/tempZone/home/vault-without-research")
    ctx.uuGroupRemove("vault-without-research", "", "")
    return result


def _test_get_latest_vault_metadata_path_empty(ctx):
    tmp_collection = _create_tmp_collection(ctx)
    latest_file = meta.get_latest_vault_metadata_path(ctx, tmp_collection)
    collection.remove(ctx, tmp_collection)
    return latest_file is None


def _test_get_latest_vault_metadata_path_normal(ctx):
    tmp_collection = _create_tmp_collection(ctx)
    data_object.write(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869873].json"), "test")
    data_object.write(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869875].json"), "test")
    data_object.write(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869877].json"), "test")
    data_object.write(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869876].json"), "test")
    data_object.write(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869874].json"), "test")
    latest_file = meta.get_latest_vault_metadata_path(ctx, tmp_collection)
    data_object.remove(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869873].json"))
    data_object.remove(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869875].json"))
    data_object.remove(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869877].json"))
    data_object.remove(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869876].json"))
    data_object.remove(ctx, os.path.join(tmp_collection, "yoda-metadata[1722869874].json"))
    collection.remove(ctx, tmp_collection)
    return latest_file == os.path.join(tmp_collection, "yoda-metadata[1722869877].json")


def _test_folder_secure_func(ctx, func):
    """Create tmp collection, apply func to it and get result, and clean up.
       Used for testing functions that modify avu/acls related to folder secure.
       Happy flow.

    :param ctx:  Combined type of a callback and rei struct
    :param func: Function to test

    :returns: Result of action
    """
    tmp_coll = _create_tmp_collection(ctx)
    # Assume returns True/False, or does not return
    result = func(ctx, tmp_coll)
    # Needed to be able to delete collection in situations where func changed ACLs
    msi.set_acl(ctx, "default", "admin:own", user.full_name(ctx), tmp_coll)
    collection.remove(ctx, tmp_coll)
    if result is None:
        return True
    return result


def _test_diff_data_describe_changes(ctx, data_name):
    """Runs util.diff_data.describe_metadata_changes against a particular
       set of data

    :param ctx:           Combined type of a callback and rei struct
    :param data_name:     Name of data to test

    :returns: Result change description list
    :raises Exception: If data_name does not refer to a known test data name
    """
    data1 = {"key1": "value1", "key2": "value2", "key3": "value3", "key4": "value4", "key5": "value5", "key6": "value6", "key7": {"nestedkey": "nestedvalue"}}
    data2 = data1.copy()

    if data_name == "same_data":
        pass
    elif data_name == "onevaluechanged":
        data2["key1"] = "value_modified"
    elif data_name == "twovalueschanged":
        data2["key1"] = "value_modified"
        data2["key2"] = "value_modified"
    elif data_name == "sixvalueschanged":
        for i in range(1, 7):
            data2["key" + str(i)] = "value_modified"
    elif data_name == "nestedvaluechanged":
        data2["key7"]["nestedkey"] = "value_modified"
    elif data_name == "keyadded":
        data2["newkey"] = "newvalue"
    else:
        raise Exception("Unknown data name when testing diff_data.describe_metadata_changes.")

    return diff_data.describe_metadata_changes(data1, data2)


basic_integration_tests = [
    {"name": "msvc.json_arrayops.add",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "d", "add", 0, 0),
     "check": lambda x: x == '["a", "b", "c", "d"]'},
    {"name": "msvc.json_arrayops.find_exist",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "b", "find", 0, 3),
     "check": lambda x: x == 1},
    {"name": "msvc.json_arrayops.find_notexist",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "d", "find", 0, 3),
     "check": lambda x: x == -1},
    {"name": "msvc.json_arrayops.get",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "", "get", 1, 1),
     "check": lambda x: x == 'b'},
    {"name": "msvc.json_arrayops.rm_exist",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "b", "rm", 0, 0),
     "check": lambda x: x == '["a", "c"]'},
    {"name": "msvc.json_arrayops.rm_notexist",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "d", "rm", 0, 0),
     "check": lambda x: x == '["a", "b", "c"]'},
    {"name": "msvc.json_arrayops.size",
     "test": lambda ctx: _call_msvc_json_arrayops(ctx, '["a", "b", "c"]', "", "size", 0, 3),
     "check": lambda x: x == 3},
    {"name": "msvc.json_objops.add_notexist_empty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '', msi.kvpair(ctx, "e", "f"), 'add', 0),
     "check": lambda x: x == '{"e": "f"}'},
    {"name": "msvc.json_objops.add_notexist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "f"), 'add', 0),
     "check": lambda x: x == '{"a": "b", "e": "f"}'},
    {"name": "msvc.json_objops.add_exist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "g"), 'add', 0),
     "check": lambda x: x == '{"a": "b", "e": "g"}'},
    {"name": "msvc.json_objops.get_exist",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b", "c": "d"}', msi.kvpair(ctx, "c", ""), 'get', 1),
     "check": lambda x: str(x) == "(['c'], ['d'])"},
    {"name": "msvc.json_objops.get_notexist",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b", "c": "d"}', msi.kvpair(ctx, "e", ""), 'get',  1),
     "check": lambda x: str(x) == "(['e'], [''])"},
    {"name": "msvc.json_objops.rm_exist",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b", "c": "d"}', msi.kvpair(ctx, "c", "d"), 'rm',  0),
     "check": lambda x: x == '{"a": "b"}'},
    {"name": "msvc.json_objops.rm_notexist",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b", "c": "d"}', msi.kvpair(ctx, "c", "e"), 'rm',  0),
     "check": lambda x: x == '{"a": "b", "c": "d"}'},
    {"name": "msvc.json_objops.set_notexist_empty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '', msi.kvpair(ctx, "e", "f"), 'set',  0),
     "check": lambda x: x == '{"e": "f"}'},
    {"name": "msvc.json_objops.set_notexist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "f"), 'set',  0),
     "check": lambda x: x == '{"a": "b", "e": "f"}'},
    {"name": "msvc.json_objops.set_exist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "g"), 'set',  0),
     "check": lambda x: x == '{"a": "b", "e": "g"}'},
    {"name": "msvc.msi_vault_stat.file",
     "test": lambda ctx: (_call_msvc_stat_vault(ctx, "dev001_1", "/var/lib/irods/Vault1_1/yoda/licenses/GNU General Public License v3.0.uri"),
                          _call_msvc_stat_vault(ctx, "dev001_2", "/var/lib/irods/Vault1_2/yoda/licenses/GNU General Public License v3.0.uri")),
     "check": lambda x: (x[0][0] == "FILE" and x[0][1] == "45") or (x[1][0] == "FILE" and x[1][1] == "45")},
    {"name": "msvc.msi_vault_stat.dir",
     "test": lambda ctx: (_call_msvc_stat_vault(ctx, "dev001_1", "/var/lib/irods/Vault1_1/home"),
                          _call_msvc_stat_vault(ctx, "dev001_2", "/var/lib/irods/Vault1_2/home")),
     "check": lambda x: (x[0][0] == "DIR" and x[0][1] == "0") or (x[1][0] == "DIR" and x[1][1] == "0")},
    {"name": "msvc.msi_vault_stat.notexist",
     "test": lambda ctx: _call_msvc_stat_vault(ctx, "dev001_1", "/var/lib/irods/Vault1_1/doesnotexist"),
     "check": lambda x: x[0] == "NOTEXIST" and x[1] == "0"},
    {"name": "msvc.msi_vault_stat.resourcenotexist",
     "test": lambda ctx: _call_msvc_stat_vault_check_exc(ctx, "doesnotexist", "/var/lib/irods/Vault1_1/yoda/licenses/GNU General Public License v3.0.uri"),
     "check": lambda x: x},
    {"name": "msvc.msi_vault_stat.outsidevault1",
     "test": lambda ctx: _call_msvc_stat_vault_check_exc(ctx, "dev001_1", "/etc/passwd"),
     "check": lambda x: x},
    {"name": "msvc.msi_vault_stat.outsidevault2",
     "test": lambda ctx: _call_msvc_stat_vault_check_exc(ctx, "dev001_1", "/var/lib/irods/Vault1_2/yoda/licenses/GNU General Public License v3.0.uri"),
     "check": lambda x: x},
    {"name": "msvc.msi_file_checksum.file",
     "test": lambda ctx: _call_file_checksum_either_resc(ctx, "/var/lib/irods/VaultX/yoda/licenses/GNU General Public License v3.0.txt"),
     "check": lambda x: x == "sha2:OXLcl0T2SZ8Pmy2/dmlvKuetivmyPd5m1q+Gyd+zaYY="},
    {"name": "msvc.msi_file_checksum.file_not_exist",
     "test": lambda ctx: _call_file_checksum_check_exc(ctx, '/var/lib/irods/Vault1_2/yoda/licenses/doesnotexist.txt', 'dev001_2'),
     "check": lambda x: x},
    {"name": "msvc.msi_file_checksum.resc_not_exist",
     "test": lambda ctx: _call_file_checksum_check_exc(ctx, '/var/lib/irods/Vault1_1/yoda/licenses/GNU General Public License v3.0.txt', 'non-existent-resource'),
     "check": lambda x: x},
    {"name": "msvc.msi_file_checksum.outside_vault",
     "test": lambda ctx: _call_file_checksum_check_exc(ctx, '/etc/passwd', 'dev001_2'),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.dir",
     "test": lambda ctx: _call_dir_list(ctx, "/var/lib/irods/Vault1_1/yoda", "dev001_1"),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.dir_not_exist",
     "test": lambda ctx: _call_dir_list_check_exc(ctx, '/var/lib/irods/Vault1_2/yoda/doesnotexist', 'dev001_2'),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.file_resc_1",
     "test": lambda ctx: _call_dir_list_check_exc(ctx, '/var/lib/irods/Vault1_1/yoda/licenses/GNU General Public License v3.0.txt', 'dev001_1'),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.file_resc_2",
     "test": lambda ctx: _call_dir_list_check_exc(ctx, '/var/lib/irods/Vault1_2/yoda/licenses/GNU General Public License v3.0.txt', 'dev001_2'),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.resc_not_exist",
     "test": lambda ctx: _call_dir_list_check_exc(ctx, '/var/lib/irods/Vault1_1/yoda', 'non-existent-resource'),
     "check": lambda x: x},
    {"name": "msvc.msi_dir_list.outside_vault",
     "test": lambda ctx: _call_dir_list_check_exc(ctx, '/etc/passwd', 'dev001_2'),
     "check": lambda x: x},
    {"name": "avu.associate_to_coll",
     "test": lambda ctx: _test_avu_associate_to_coll(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x and len(x) == 1)},
    {"name": "avu.associate_to_data",
     "test": lambda ctx: _test_avu_associate_to_data(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.set_from_coll.catch.yes",
     "test": lambda ctx: _test_avu_set_collection(ctx, True),
     "check": lambda x: (("foo", "bar", "") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.set_from_coll.catch.no",
     "test": lambda ctx: _test_avu_set_collection(ctx, False),
     "check": lambda x: (("foo", "bar", "") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.rmw_from_coll_wildcard.catch.yes",
     "test": lambda ctx: _test_avu_rmw_collection(ctx, ("foo", "%", "%", True)),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.rmw_from_coll_wildcard.catch.no",
     "test": lambda ctx: _test_avu_rmw_collection(ctx, ("foo", "%", "%", False)),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.get_attr_val_of_coll.exists.yes",
     "test": lambda ctx: _test_avu_get_attr_val_of_coll(ctx, "foo", "bar"),
     "check": lambda x: x == "bar"},
    {"name": "avu.get_attr_val_of_coll.exists.no",
     "test": lambda ctx: _test_avu_get_attr_val_of_coll_exception(ctx),
     "check": lambda x: x},
    {"name": "avu.apply_atomic_operations.collection",
     "test": lambda ctx: _test_msvc_apply_atomic_operations_collection(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x and len(x) == 1)},
    {"name": "avu.apply_atomic_operations.data_object",
     "test": lambda ctx: _test_msvc_apply_atomic_operations_object(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.apply_atomic_operations.invalid",
     "test": lambda ctx: avu.apply_atomic_operations(ctx, {"inspector": "gadget"}),
     "check": lambda x: not x},
    {"name": "jsonutil.set_on_object.collection",
     "test": lambda ctx: _test_jsonutil_set_on_object_collection(ctx),
     "check": lambda x: (("inspector", "gadget", "root_0_s") in x and len(x) == 1)},
    {"name": "jsonutil.set_on_object.data_object",
     "test": lambda ctx: _test_jsonutil_set_on_object_data_object(ctx),
     "check": lambda x: (("inspector", "gadget", "root_0_s") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "data_access_token.get_all_tokens",
     "test": lambda ctx: data_access_token.get_all_tokens(ctx),
     "check": lambda x: isinstance(x, list)},
    {"name": "folder.get_datamanager_coll",
     "test": lambda ctx: folder.get_datamanager_coll(ctx, "/tempZone/home/research-default-3"),
     "check": lambda x: x == "/tempZone/home/datamanager-test-automation"},
    {"name": "folder.get_datamanager_coll",
     "test": lambda ctx: folder.get_datamanager_coll(ctx, "/tempZone/home/not-research-group-not-exist/folder-not-exist"),
     "check": lambda x: x is None},
    {"name": "folder.get_datamanagers",
     "test": lambda ctx: folder.get_datamanagers(ctx, "/tempZone/home/research-default-3"),
     "check": lambda x: isinstance(x, list) and sorted(x) == [(username, "tempZone") for username in ["datamanager", "datamanager@yoda.test", "functionaladminpriv", "functionaladminpriv@yoda.test"]]},
    {"name":  "folder.set_can_modify",
     "test": lambda ctx: _test_folder_secure_func(ctx, folder.set_can_modify),
     "check": lambda x: x},
    {"name":  "folder.cronjob_status",
     "test": lambda ctx: _test_folder_cronjob_status(ctx),
     "check": lambda x: x[0] and x[1] and x[2]},
    {"name":  "folder.set_get_last_run_time",
     "test": lambda ctx: _test_folder_set_get_last_run(ctx),
     "check": lambda x: x[0] and x[1] and x[2] + 25 >= int(time.time())},
    {"name":  "folder.set_last_run_time",
     "test": lambda ctx: _test_folder_secure_func(ctx, folder.set_last_run_time),
     "check": lambda x: x},
    {"name":  "folder.check_folder_secure",
     "test": lambda ctx: _test_folder_secure_func(ctx, folder.check_folder_secure),
     "check": lambda x: x},
    {"name":  "folder.folder_secure_fail",
     "test": lambda ctx: _test_folder_secure_func(ctx, folder.folder_secure_fail),
     "check": lambda x: x},
    {"name":  "folder.set_retry_avus",
     "test": lambda ctx: _test_folder_set_retry_avus(ctx),
     "check": lambda x: x},
    {"name":  "folder.determine_new_vault_target.research",
     "test": lambda ctx: folder.determine_new_vault_target(ctx, "/tempZone/home/research-initial/testdata"),
     "check": lambda x: re.match(r"^\/tempZone\/home\/vault-initial\/testdata\[[0-9]*\]$", x) is not None},
    {"name":  "folder.determine_new_vault_target.deposit",
     "test": lambda ctx: folder.determine_new_vault_target(ctx, "/tempZone/home/deposit-pilot/deposit-hi[123123]"),
     "check": lambda x: re.match(r"^\/tempZone\/home\/vault-pilot\/deposit-hi\[[0-9]*\]\[[0-9]*\]$", x) is not None},
    {"name":  "folder.determine_new_vault_target.invalid",
     "test": lambda ctx: folder.determine_new_vault_target(ctx, "/tempZone/home/not-research-group-not-exist/folder-not-exist"),
     "check": lambda x: x == ""},
    {"name":  "groups.get_groups_data.vault",
     "test": lambda ctx: _test_groups_data(ctx, "vault-default-3", "schema_id", "default-3"),
     "check": lambda x: x},
    {"name":  "groups.get_groups_data.public.category",
     "test": lambda ctx: _test_groups_data(ctx, "public", "category", "integration-test-cat"),
     "check": lambda x: x},
    {"name":  "groups.get_groups_data.public.subcategory",
     "test": lambda ctx: _test_groups_data(ctx, "public", "subcategory", "integration-test-subcat"),
     "check": lambda x: x},
    {"name":  "groups.get_groups_data.public.schema_id",
     "test": lambda ctx: _test_groups_data(ctx, "public", "schema_id", "default-3"),
     "check": lambda x: x},
    {"name": "groups.rule_group_expiration_date_validate.1",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate("", ""),
     "check": lambda x: x['arguments'][1] == 'true'},
    {"name": "groups.rule_group_expiration_date_validate.2",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate(".", ""),
     "check": lambda x: x['arguments'][1] == 'true'},
    {"name": "groups.rule_group_expiration_date_validate.3",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate("abc", ""),
     "check": lambda x: x['arguments'][1] == 'false'},
    {"name": "groups.rule_group_expiration_date_validate.4",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate("2020-02-02", ""),
     "check": lambda x: x['arguments'][1] == 'false'},
    {"name": "groups.rule_group_expiration_date_validate.5",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate("2044-01-32", ""),
     "check": lambda x: x['arguments'][1] == 'false'},
    {"name": "groups.rule_group_expiration_date_validate.6",
     "test": lambda ctx: ctx.rule_group_expiration_date_validate("2044-02-26", ""),
     "check": lambda x: x['arguments'][1] == 'true'},
    {"name": "meta.get_latest_vault_metadata_path.empty",
     "test": lambda ctx: _test_get_latest_vault_metadata_path_empty(ctx),
     "check": lambda x: x},
    {"name": "meta.get_latest_vault_metadata_path.normal",
     "test": lambda ctx: _test_get_latest_vault_metadata_path_normal(ctx),
     "check": lambda x: x},
    {"name": "policies.check_anonymous_access_allowed.local",
     "test": lambda ctx: ctx.rule_check_anonymous_access_allowed("127.0.0.1", ""),
     "check": lambda x: x['arguments'][1] == 'true'},
    {"name": "policies.check_anonymous_access_allowed.remote",
     "test": lambda ctx: ctx.rule_check_anonymous_access_allowed("1.2.3.4", ""),
     "check": lambda x: x['arguments'][1] == 'false'},
    {"name": "policies.check_max_connections_exceeded",
     "test": lambda ctx: ctx.rule_check_max_connections_exceeded(""),
     # This rule should always return 'false' for user 'rods'
     "check": lambda x: x['arguments'][0] == 'false'},
    {"name":  "research.api_research_manifest.research",
     "test": lambda ctx: research.research_manifest(ctx, "/tempZone/home/research-initial"),
     "check": lambda x: x['files'] > 1 and x['size'] != "0 B" and len(x['manifest']) > 1},
    {"name":  "research.api_research_manifest.vault",
     "test": lambda ctx: research.research_manifest(ctx, "/tempZone/home/vault-initial"),
     "check": lambda x: x['files'] == 0 and x['size'] == "0 B" and x['manifest'] == []},
    {"name":  "research.api_research_manifest.deposit",
     "test": lambda ctx: research.research_manifest(ctx, "/tempZone/home/deposit-pilot"),
     "check": lambda x: x['files'] == 0 and x['size'] == "0 B" and x['manifest'] == []},
    {"name":  "research.api_research_manifest.invalid_path",
     "test": lambda ctx: research.research_manifest(ctx, "/tempZone/does/not/exist"),
     "check": lambda x: isinstance(x, api.Error)},
    {"name":  "research.api_research_manifest.no_space",
     "test": lambda ctx: research.research_manifest(ctx, "/tempZone/yoda/schemas"),
     "check": lambda x: isinstance(x, api.Error)},
    {"name":  "schema.get_active_schema_path.deposit",
     "test": lambda ctx: schema.get_active_schema_path(ctx, "/tempZone/home/deposit-pilot"),
     "check": lambda x: x == "/tempZone/yoda/schemas/dag-0/metadata.json"},
    {"name":  "schema.get_active_schema_path.deposit-from-default",
     "test": lambda ctx: _test_schema_active_schema_deposit_from_default(ctx),
     "check": lambda x: x == "/tempZone/yoda/schemas/default-3/metadata.json"},
    {"name":  "schema.get_active_schema_path.research",
     "test": lambda ctx: schema.get_active_schema_path(ctx, "/tempZone/home/research-core-2"),
     "check": lambda x: x == "/tempZone/yoda/schemas/core-2/metadata.json"},
    {"name":  "schema.get_active_schema_path.research-from-default",
     "test": lambda ctx: _test_schema_active_schema_research_from_default(ctx),
     "check": lambda x: x == "/tempZone/yoda/schemas/default-3/metadata.json"},
    {"name":  "schema.get_active_schema_path.vault-deposit",
     "test": lambda ctx: schema.get_active_schema_path(ctx, "/tempZone/home/vault-pilot"),
     "check": lambda x: x == "/tempZone/yoda/schemas/dag-0/metadata.json"},
    {"name":  "schema.get_active_schema_path.vault-research",
     "test": lambda ctx: schema.get_active_schema_path(ctx, "/tempZone/home/vault-core-2"),
     "check": lambda x: x == "/tempZone/yoda/schemas/core-2/metadata.json"},
    {"name":  "schema.get_active_schema_path.vault-research-override",
     "test": lambda ctx: _test_schema_active_schema_vault_research_override(ctx),
     "check": lambda x: x == "/tempZone/yoda/schemas/integration-test-schema-1/metadata.json"},
    {"name":  "schema.get_active_schema_path.vault-without-research",
     "test": lambda ctx: _test_schema_active_schema_vault_without_research(ctx),
     "check": lambda x: x == "/tempZone/yoda/schemas/default-3/metadata.json"},
    # Vault metadata schema report: only check return value type, not contents
    {"name": "schema_transformation.batch_vault_metadata_schema_report",
     "test": lambda ctx: ctx.rule_batch_vault_metadata_schema_report(""),
     "check": lambda x: isinstance(json.loads(x['arguments'][0]), dict)},
    {"name": "statistics.exportdata",
     "test": lambda ctx: _test_statistics_exportdata(ctx),
     "check": lambda x: x == []},
    {"name": "statistics.get_user_groups_for_stats.rods.without_filter",
     "test": lambda ctx: get_user_groups_for_stats(ctx),
     "check": lambda x: len(x) >= 25 and "research-default-1" in x},
    {"name": "statistics.get_user_groups_for_stats.rods.with_filter",
     "test": lambda ctx: get_user_groups_for_stats(ctx, search_filter="AND USER_GROUP_NAME = 'research-default-1'"),
     "check": lambda x: x == ["research-default-1"]},
    {"name": "statistics.get_user_groups_for_stats.researcher",
     "test": lambda ctx: get_user_groups_for_stats(ctx, user_name="researcher"),
     "check": lambda x: sorted(x) == sorted(['deposit-pilot', 'grp-intake-initial', 'grp-intake-test', 'intake-test2', 'research-core-0', 'research-core-1', 'research-core-2', 'research-dag-0', 'research-default-0', 'research-default-1', 'research-default-2', 'research-default-3', 'research-epos-msl-0', 'research-hptlab-0', 'research-hptlab-1', 'research-initial', 'research-initial1', 'research-revisions', 'research-smoke-test', 'research-teclab-0', 'research-teclab-1', 'research-vollmer-0'])},
    {"name": "statistics.get_user_groups_for_stats.datamanager",
     "test": lambda ctx: get_user_groups_for_stats(ctx, user_name="datamanager"),
     "check": lambda x: sorted(x) == sorted(['grp-datamanager-initial', 'grp-datamanager-test', 'grp-datamanager-test2', 'grp-intake-initial', 'grp-intake-test', 'intake-test2', 'research-smoke-test', 'deposit-pilot', 'deposit-pilot1', 'research-core-0', 'research-core-1', 'research-core-2', 'research-dag-0', 'research-default-0', 'research-default-1', 'research-default-2', 'research-default-3', 'research-epos-msl-0', 'research-hptlab-0', 'research-hptlab-1', 'research-initial', 'research-initial1', 'research-revisions', 'research-teclab-0', 'research-teclab-1', 'research-vollmer-0'])},
    {"name": "statistics.get_user_groups_for_stats.viewer",
     "test": lambda ctx: get_user_groups_for_stats(ctx, user_name="viewer"),
     "check": lambda x: sorted(x) == sorted(['deposit-pilot', 'deposit-pilot1'])},
    {"name":  "util.collection.exists.yes",
     "test": lambda ctx: collection.exists(ctx, "/tempZone/yoda"),
     "check": lambda x: x},
    {"name":   "util.collection.exists.no",
     "test": lambda ctx: collection.exists(ctx, "/tempZone/chewbacca"),
     "check": lambda x: not x},
    {"name":   "util.collection.owner",
     "test": lambda ctx: collection.owner(ctx, "/tempZone/yoda"),
     "check": lambda x: x == ('rods', 'tempZone')},
    {"name":   "util.collection.subcollections",
     "test": lambda ctx: _test_collection_subcollections(ctx),
     "check": lambda x: x},
    {"name":   "util.collection.to_from_id",
     "test": lambda ctx: collection.name_from_id(ctx, collection.id_from_name(ctx, "/tempZone/home/research-initial")),
     "check": lambda x: x == "/tempZone/home/research-initial"},
    {"name":   "util.data_object.exists.yes",
     "test": lambda ctx: data_object.exists(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x},
    {"name":   "util.data_object.exists.no",
     "test": lambda ctx: data_object.exists(ctx, "/tempZone/home/research-initial/testdata/doesnotexist.txt"),
     "check": lambda x: not x},
    {"name": "util.data_object.get_properties.by_data_name",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["DATA_NAME"] == "lorem.txt"},
    {"name": "util.data_object.get_properties.by_modify_time",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["DATA_MODIFY_TIME"].isdigit()},
    {"name": "util.data_object.get_properties.by_owner_name",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["DATA_OWNER_NAME"] == "rods"},
    {"name": "util.data_object.get_properties.by_coll_name",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["COLL_NAME"] == "/tempZone/home/research-initial/testdata"},
    {"name": "util.data_object.get_properties.by_coll_id",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["COLL_ID"].isdigit()},
    {"name": "util.data_object.get_properties.by_data_resc_hier",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["DATA_RESC_HIER"].startswith('irodsResc')},
    {"name": "util.data_object.get_properties.by_data_size",
     "test": lambda ctx: data_object.get_properties(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"), "irodsResc"),
     "check": lambda x: x["DATA_SIZE"].isdigit()},
    # Using the resource_id as data_id to ensure no existing data object uses this occupied identifier
    {"name":   "util.data_object.get_properties.no_data_object",
     "test": lambda ctx: data_object.get_properties(ctx, resources.id_from_name(ctx, "irodsResc"), "irodsResc"),
     "check": lambda x: x is None},
    {"name":   "util.data_object.owner",
     "test": lambda ctx: data_object.owner(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == ('rods', 'tempZone')},
    {"name":   "util.data_object.size",
     "test": lambda ctx: data_object.size(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == 1003240},
    {"name":   "util.data_object.to_from_id",
     "test": lambda ctx: data_object.name_from_id(ctx, data_object.id_from_path(ctx, "/tempZone/home/research-initial/testdata/lorem.txt")),
     "check": lambda x: x == "/tempZone/home/research-initial/testdata/lorem.txt"},
    {"name":   "util.data_object.get_group_owners",
     "test": lambda ctx: data_object.get_group_owners(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == [['research-initial', 'tempZone']]},
    {"name":   "util.diff_data.describe_metadata_changes.same_data",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "same_data"),
     "check": lambda x: x  == []},
    {"name":   "util.diff_data.describe_metadata_changes.onevaluechanged",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "onevaluechanged"),
     "check": lambda x: x  == ['modified metadata: key1']},
    {"name":   "util.diff_data.describe_metadata_changes.twovalueschanged",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "twovalueschanged"),
     "check": lambda x: x  == ['modified metadata: key1, key2']},
    {"name":   "util.diff_data.describe_metadata_changes.sixvalueschanged",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "sixvalueschanged"),
     "check": lambda x: x  == ['modified metadata: key1, key2, key3, key4 and more']},
    {"name":   "util.diff_data.describe_metadata_changes.keyadded",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "keyadded"),
     "check": lambda x: x  == ['added metadata: newkey']},
    {"name":   "util.diff_data.describe_metadata_changes.nestedvaluechanged",
     "test": lambda ctx: _test_diff_data_describe_changes(ctx, "nestedvaluechanged"),
     "check": lambda x: x  == []},
    {"name":   "util.group.exists.yes",
     "test": lambda ctx: group.exists(ctx, "research-initial"),
     "check": lambda x: x},
    {"name":   "util.group.exists.no",
     "test": lambda ctx: group.exists(ctx, "research-doesnotexist"),
     "check": lambda x: not x},
    {"name":   "util.group.get_category",
     "test": lambda ctx: group.get_category(ctx, "research-initial"),
     "check": lambda x: x == "test-automation"},
    {"name":   "util.group.is_member.yes",
     "test": lambda ctx: group.is_member(ctx, "research-initial", "researcher"),
     "check": lambda x: x},
    {"name":   "util.group.is_member.no",
     "test": lambda ctx: group.is_member(ctx, "research-initial", "rods"),
     "check": lambda x: not x},
    {"name":   "util.group.members.normal",
     "test": lambda ctx: group.members(ctx, "research-initial"),
     "check": lambda x: sorted(x) == sorted([('functionaladminpriv', 'tempZone'), ('functionaladminpriv@yoda.test', 'tempZone'), ('groupmanager', 'tempZone'), ('groupmanager@yoda.test', 'tempZone'), ('researcher', 'tempZone'), ('researcher@yoda.test', 'tempZone')])},
    {"name":   "util.group.members.doesnotexist",
     "test": lambda ctx: user.exists(ctx, "research-doesnotexist"),
     "check": lambda x: x is False},
    {"name":   "util.resources.exists.yes",
     "test": lambda ctx: resources.exists(ctx, "irodsResc"),
     "check": lambda x: x},
    {"name":   "util.resources.exists.no",
     "test": lambda ctx: resources.exists(ctx, "bananaResc"),
     "check": lambda x: not x},
    {"name":   "util.resources.get_all_resource_names",
     "test": lambda ctx: resources.get_all_resource_names(ctx),
     "check": lambda x: len(x) == 15},
    {"name":   "util.resources.get_children_by_name",
     "test": lambda ctx: resources.get_children_by_name(ctx, "dev001_p1"),
     "check": lambda x: x == ["dev001_1"]},
    {"name":   "util.resources.get_parent_by_name",
     "test": lambda ctx: resources.get_parent_by_name(ctx, "dev001_1"),
     "check": lambda x: x == "dev001_p1"},
    {"name":   "util.resources.get_resource_names_by_type",
     "test": lambda ctx: resources.get_resource_names_by_type(ctx, "unixfilesystem"),
     "check": lambda x: sorted(x) == sorted(['bundleResc', 'dev001_1', 'dev001_2', 'dev002_1'])},
    {"name":   "util.resources.get_type_by_name",
     "test": lambda ctx: resources.get_type_by_name(ctx, "dev001_1"),
     "check": lambda x: x == "unixfilesystem"},
    {"name":   "util.resources.to_from_id",
     "test": lambda ctx: resources.name_from_id(ctx, resources.id_from_name(ctx, "irodsResc")),
     "check": lambda x: x == "irodsResc"},
    {"name":   "util.resources.get_children_by_id",
     "test": lambda ctx: resources.get_children_by_id(ctx, resources.id_from_name(ctx, "dev001_p1")),
     "check": lambda ctx, x: x == [resources.id_from_name(ctx, "dev001_1")]},
    {"name":   "util.resources.get_parent_by_id",
     "test": lambda ctx: resources.get_parent_by_id(ctx, resources.id_from_name(ctx, "dev001_1")),
     "check": lambda ctx, x: x == resources.id_from_name(ctx, "dev001_p1")},
    {"name":   "util.resources.get_type_by_id",
     "test": lambda ctx: resources.get_type_by_id(ctx, resources.id_from_name(ctx, "dev001_1")),
     "check": lambda x: x == "unixfilesystem"},
    {"name":   "util.user.exists.yes",
     "test": lambda ctx: user.exists(ctx, "rods"),
     "check": lambda x: x},
    {"name":   "util.user.exists.no",
     "test": lambda ctx: user.exists(ctx, "rododendron"),
     "check": lambda x: not x},
    {"name":   "util.user.is_rodsadmin.yes",
     "test": lambda ctx: user.is_rodsadmin(ctx, "rods"),
     "check": lambda x: x},
    {"name":   "util.user.is_rodsadmin.no",
     "test": lambda ctx: user.is_rodsadmin(ctx, "researcher"),
     "check": lambda x: not x},
    {"name":   "util.user.is_member_of.yes",
     "test": lambda ctx: user.is_member_of(ctx, "research-initial", "researcher"),
     "check": lambda x: x},
    {"name":   "util.user.is_member_of.no",
     "test": lambda ctx: user.is_member_of(ctx, "research-initial", "datamanager"),
     "check": lambda x: not x},
    {"name":   "util.user.number_of_connection",
     "test": lambda ctx: user.number_of_connections(ctx),
     "check": lambda x: isinstance(x, int) and x > 0},
    {"name":   "util.user.to_from_id",
     "test": lambda ctx: user.name_from_id(ctx, user.id_from_name(ctx, "researcher")),
     "check": lambda x: x == "researcher"},
    {"name":   "util.user.usertype.rodsadmin",
     "test": lambda ctx: user.get_type(ctx, "rods"),
     "check": lambda x: x == "rodsadmin"},
    {"name":   "util.user.usertype.rodsuser",
     "test": lambda ctx: user.get_type(ctx, "researcher"),
     "check": lambda x: x == "rodsuser"},
    {"name":   "is_user_external.internal",
     "test": lambda ctx: _test_is_user_external(ctx, "researcher@yoda.dev"),
     "check": lambda x: x == 1},
    {"name":   "is_user_external.external",
     "test": lambda ctx: _test_is_user_external(ctx, "researcher@externaldomain.nl"),
     "check": lambda x: x == 0},
    {"name":   "vault.copy_acls_from_parent",
     "test": lambda ctx: _test_copy_acls_from_parent(ctx),
     "check": lambda x: x == []},
    {"name": "hashes_collection.script",
     "test": lambda ctx: _test_hashes_collection_script(ctx),
     "check": lambda x: x == '3d87794f290780e470a90b6f2a545144838577395d13d95ca3899fdb4fd705fb'},
    {"name": "hashes_collection.trailing_slash",
     "test": lambda ctx: _test_hashes_collection_trailing_slash(ctx),
     "check": lambda x: x is True},
    {"name": "hashes_collection.identical_collections",
     "test": lambda ctx: test_hashes_on_identical_collections(ctx),
     "check": lambda x: x is True},
    {"name": "copy_folder_to_research.copied_correctly",
     "test": lambda ctx: _test_copy_folder_to_research(ctx),
     "check": lambda x: x is True}
]


@rule.make(inputs=[0], outputs=[1])
def rule_run_integration_tests(ctx, tests):
    """This function runs the integration tests. It must be run by
    a rodsadmin user on a development environment. It assumes the standard
    test data is present.

    :param ctx:  Combined type of a callback and rei struct
    :param tests: Indicates which tests to run:
                  - Empty string means all tests
                  - String ending with '*' means all tests that start with a prefix, e.g. 'util.user.*'
                  - Otherwise the string should be the exact name of a test

    :returns: string with test results. Each line has one test name and its verdict.
    """

    if config.measure_coverage:
        cov = measure_coverage.start_coverage()

    return_value = ""
    log.write(ctx, "Running")

    if config.environment != "development":
        log.write(ctx, "Error: integration tests can only run on development environment.")
        return ""

    if not user.is_rodsadmin(ctx):
        log.write(ctx, "Error: integration tests can only be run by a rodsadmin user.")
        return ""

    for testconfig in basic_integration_tests:
        name = testconfig["name"]
        test = testconfig["test"]
        check = testconfig["check"]

        exception = False

        if (tests != ""
                and tests != name
                and not (tests.endswith("*") and name.startswith(tests[0:-1]))):
            continue

        try:
            result = test(ctx)
        except BaseException:
            log.write(ctx, "Basic integration test {} failed with Exception: {}".format(name, traceback.format_exc()))
            exception = True

        if exception:
            verdict = "VERDICT_EXCEPTION"
        elif check.__code__.co_argcount == 1 and check(result):
            verdict = "VERDICT_OK"
        elif check.__code__.co_argcount == 2 and check(ctx, result):
            verdict = "VERDICT_OK"
        else:
            verdict = "VERDICT_FAILED   (output '{}')".format(str(result))

        return_value += name + " " + verdict + "\n"

    if config.measure_coverage:
        measure_coverage.stop_coverage(cov)

    return return_value


def _call_file_checksum_either_resc(ctx, filename):
    """Returns result of file checksum microservice for either of the
       two main UFS resources (dev001_1, dev001_2). If one returns an
       exception, we try the other.

       :param ctx: combined type of a callback and rei struct
       :param filename: name of file to checksum

       :returns: output of file checksum microservice
    """
    if config.enable_nfs_resource:
        filename = filename.replace("/var/lib/irods/", "/nfs/")
    try:
        vault_filename = filename.replace("VaultX", "Vault1_1")
        ret = msi.file_checksum(ctx, vault_filename, 'dev001_1', '')
    except Exception:
        vault_filename = filename.replace("VaultX", "Vault1_2")
        ret = msi.file_checksum(ctx, vault_filename, 'dev001_2', '')
    return ret['arguments'][2]


def _call_file_checksum_check_exc(ctx, filename, resc_name):
    """Verifies whether a call to the file checksum microservice raises an exception"""
    try:
        msi.file_checksum(ctx, filename, resc_name, '')
        return False
    except Exception:
        return True


def _call_dir_list(ctx, dirname, resc_name):
    if config.enable_nfs_resource:
        dirname = dirname.replace("/var/lib/irods/", "/nfs/")
    ret = msi.dir_list(ctx, dirname, resc_name, "")
    print(ret['arguments'][2])
    result_len = len(json.loads(ret['arguments'][2]))
    dir_len = len([entry for entry in os.listdir(dirname) if os.path.isdir(dirname + '/' + entry)])
    return result_len == dir_len


def _test_is_user_external(ctx, username):
    command = ["/etc/irods/yoda-ruleset/tools/is-user-external.py"]
    environment = dict(os.environ)
    environment["PAM_USER"] = username
    process = Popen(command, stdout=PIPE, env=environment)
    process.communicate()
    return process.wait()


def _call_dir_list_check_exc(ctx, dirname, resc_name):
    try:
        msi.dir_list(ctx, dirname, resc_name, "")
        return False
    except Exception:
        return True


def _get_hash(ctx, coll_path):
    """Run hashes_collection.sh on a collection path and return the SHA256 hash.

    :param ctx: combined type of a callback and rei struct
    :param coll_path: path to collection to hash

    :returns: the calculated SHA256 hash of the collection

    :raises RuntimeError: if script fails
    """
    script_path = "/etc/irods/yoda-ruleset/tools/hashes_collection.sh"

    if not os.access(script_path, os.X_OK):
        raise RuntimeError(f"Script {script_path} is not executable")

    cmd = [script_path, coll_path]
    environment = dict(os.environ)

    process = Popen(cmd, stdout=PIPE, stderr=PIPE, env=environment)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"hashes_collection.sh failed: {stderr.decode()}")

    # output example: "v2:<sha256hash>"
    return stdout.decode().strip().split(':', 1)[1]


def _test_hashes_collection_script(ctx):
    """Verifies that the hashes_collection.sh script produces a consistent hash.
    This is useful for testing during iRODS upgrades, as the `hashes_collection.sh`
    script utilizes `iquest`.

    :param ctx: combined type of a callback and rei struct

    :returns: the calculated SHA256 hash of the collection.
    """
    # Create collection
    coll_path = "/{}/home/rods/{}-test".format(user.zone(ctx), "hash")
    collection.create(ctx, coll_path)

    # Add data objects to collection
    data_object.write(ctx, f"{coll_path}/file1.txt", b"contentA")
    data_object.write(ctx, f"{coll_path}/file2.txt", b"contentB")

    # Create subcollection
    subcoll_path = coll_path + '/{}-test'.format("subhash")
    collection.create(ctx, subcoll_path)

    # Add data objects in subcollection
    data_object.write(ctx, f"{subcoll_path}/file3.txt", b"contentC")
    data_object.write(ctx, f"{subcoll_path}/file4.txt", b"contentD")

    hash_ = _get_hash(ctx, coll_path)

    collection.remove(ctx, subcoll_path)
    collection.remove(ctx, coll_path)

    return hash_


def _test_hashes_collection_trailing_slash(ctx):
    """Verifies that adding or omitting a trailing slash in the collection
    path does not affect the hash.

    :param ctx: combined type of a callback and rei struct

    :returns: true if the same hash is returned else false
    """
    base_path = "/{}/home/rods".format(user.zone(ctx))
    path = f"{base_path}/collection-trailing-slash"

    collection.create(ctx, path)
    data_object.write(ctx, f"{path}/file1.txt", b"abc")
    collection.create(ctx, f"{path}/sub")
    data_object.write(ctx, f"{path}/sub/file2.txt", b"123")

    # Compare hashes with and without trailing slash
    hash_no_slash = _get_hash(ctx, path)
    hash_with_slash = _get_hash(ctx, path + "/")

    data_object.remove(ctx, f"{path}/file1.txt")
    data_object.remove(ctx, f"{path}/sub/file2.txt")
    collection.remove(ctx, f"{path}/sub")
    collection.remove(ctx, path)

    return hash_no_slash == hash_with_slash


def test_hashes_on_identical_collections(ctx):
    """Verifies that two collections with the same structure
    produce identical hashes.

    :param ctx: combined type of a callback and rei struct

    :returns: true if the same hash is returned else false
    """

    base_path = f"/{user.zone(ctx)}/home/rods"
    coll1 = f"{base_path}/project"
    coll2 = f"{base_path}/project_copy"

    # Create first collection and add files + subcollection
    collection.create(ctx, coll1)
    data_object.write(ctx, f"{coll1}/file1.txt", b"contentA")
    collection.create(ctx, f"{coll1}/subdir")
    data_object.write(ctx, f"{coll1}/subdir/file2.txt", b"contentB")

    # Create second collection with the same structure and contents
    collection.create(ctx, coll2)
    data_object.write(ctx, f"{coll2}/file1.txt", b"contentA")
    collection.create(ctx, f"{coll2}/subdir")
    data_object.write(ctx, f"{coll2}/subdir/file2.txt", b"contentB")

    # Get hashes
    hash1 = _get_hash(ctx, coll1)
    hash2 = _get_hash(ctx, coll2)

    data_object.remove(ctx, f"{coll1}/file1.txt")
    data_object.remove(ctx, f"{coll1}/subdir/file2.txt")
    collection.remove(ctx, f"{coll1}/subdir")
    collection.remove(ctx, coll1)

    data_object.remove(ctx, f"{coll2}/file1.txt")
    data_object.remove(ctx, f"{coll2}/subdir/file2.txt")
    collection.remove(ctx, f"{coll2}/subdir")
    collection.remove(ctx, coll2)

    return hash1 == hash2


def _test_copy_acls_from_parent(ctx: rule.Context) -> List[str]:
    """Test for vault.copy_acls_from_parent

    :param ctx: combined type of a callback and rei struct

    :returns: list of unexpected issues
    """
    test_id = str(uuid.uuid4())
    zone = user.zone(ctx)
    main_path = f"/{zone}/home/rods/test-copy-acls-from-parent"
    sub_path = f"{main_path}/{test_id}"
    test_read_user = "datamanager"
    test_write_user = "researcher"
    test_own_user = "projectmanager"

    if not collection.exists(ctx, main_path):
        collection.create(ctx, main_path)

    msi.set_acl(ctx, "default", "read", test_read_user, main_path)
    msi.set_acl(ctx, "default", "write", test_write_user, main_path)
    msi.set_acl(ctx, "default", "own", test_own_user, main_path)

    collection.create(ctx, sub_path)
    copy_acls_from_parent(ctx, sub_path, "default")

    acls_result = list(genquery.Query(
        ctx, "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
        f"COLL_NAME = '{sub_path}'",
        output=genquery.AS_LIST))
    acls_with_names_result = [(user.name_from_id(ctx, acl[0]), acl[1]) for acl in acls_result]

    unexpected_results = []

    if (test_read_user, "read_object") not in acls_with_names_result:
        print("Read privileges not copied")
    if (test_write_user, "modify_object") not in acls_with_names_result:
        print("Write privileges not copied")
    if (test_own_user, "own") not in acls_with_names_result:
        print("Ownership privileges not copied")

    collection.remove(ctx, sub_path)
    collection.remove(ctx, main_path)
    return unexpected_results


def _test_copy_folder_to_research(ctx):
    """Test for copy-to-research's irsync function. Verify
    if files are copied correctly to research space.

    :param ctx: combined type of a callback and rei struct

    :returns: true if collection is copied to desinated research space
                and permissions are correctly set, else false
    """

    # Generate unique test identifiers
    test_id = str(uuid.uuid4())
    zone = user.zone(ctx)

    # Create test collections
    vault_origin = f"/{zone}/home/vault-initial/test_{test_id}"
    research_target = f"/{zone}/home/research-initial/test_{test_id}"

    try:
        # Setup origin in vault
        collection.create(ctx, vault_origin)
        data_object.write(ctx, f"{vault_origin}/test_file.txt", "TEST_CONTENT")

        # Execute the copy operation
        success = copy_folder_to_research(ctx, vault_origin, research_target)
        # Verify results
        results = {
            "success": success,
            "target_exists": collection.exists(ctx, f"{research_target}"),
            "file_copied": data_object.exists(ctx, f"{research_target}/test_file.txt"),
        }

        return all(results.values())

    except Exception as e:
        log.write(ctx, f"Test exception: {str(e)}")
        return False
    finally:
        # Cleanup regardless of test outcome
        for path in [vault_origin, research_target]:
            try:
                if collection.exists(ctx, path):
                    collection.remove(ctx, path)
            except Exception as e:
                log.write(ctx, f"Clean up test files exception: {str(e)}")


def _test_collection_subcollections(ctx: rule.Context) -> bool:
    """Tests for the collection.subcollections function

    :param ctx: combined type of a callback and rei struct

    :raises RuntimeError: if cleanup of test data failed

    :returns: true if tests passed, otherwise false
    """
    basepath = "/tempZone/home/rods/test_subcollections"
    testdirs = ["a1", "a1/a2", "b1", "b1/b2", "c1", "c1/c2"]

    # Set up test data
    if not collection.exists(ctx, basepath):
        collection.create(ctx, basepath)
    for testdir in testdirs:
        subpath = os.path.join(basepath, testdir)
        if not collection.exists(ctx, subpath):
            collection.create(ctx, subpath)

    result_nosub_nonr = list(collection.subcollections(ctx, os.path.join(basepath, "a1/a2")))
    if result_nosub_nonr != []:
        log.write(ctx, "test_collection_subcollections fail on empty/NR: " + str(result_nosub_nonr))
        return False

    result_nosub_rec = list(collection.subcollections(ctx, os.path.join(basepath, "a1/a2"), True))
    if result_nosub_rec != []:
        log.write(ctx, "test_collection_subcollections fail on empty/R: " + str(result_nosub_rec))
        return False

    result_l1_nonr = list(collection.subcollections(ctx, os.path.join(basepath, "a1")))
    if result_l1_nonr != [os.path.join(basepath, "a1/a2")]:
        log.write(ctx, "test_collection_subcollections fail on L1/NR: " + str(result_l1_nonr))
        return False

    result_l1_rec = list(collection.subcollections(ctx, os.path.join(basepath, "a1"), True))
    if result_l1_rec != [os.path.join(basepath, "a1/a2")]:
        log.write(ctx, "test_collection_subcollections fail on L1/R: " + str(result_l1_rec))
        return False

    result_l2_nonr = list(collection.subcollections(ctx, basepath))
    if result_l2_nonr != sorted([os.path.join(basepath, dir) for dir in ["a1", "b1", "c1"]]):
        log.write(ctx, "test_collection_subcollections fail on L2/NR: " + str(result_l2_nonr))
        return False

    result_l2_rec = list(collection.subcollections(ctx, basepath, True))
    if sorted(result_l2_rec) != sorted([os.path.join(basepath, dir) for dir in testdirs]):
        log.write(ctx, "test_collection_subcollections fail on L2/R: " + str(result_l2_rec))
        return False

    # Remove test data
    cmd = ["irm", "-r", basepath]
    environment = dict(os.environ)

    process = Popen(cmd, stdout=PIPE, stderr=PIPE, env=environment)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"failure during cleanup test data collections.subcollections {stderr.decode()}")

    return True
