# -*- coding: utf-8 -*-
"""Integration tests for the development environment."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_run_integration_tests']

import json
import os
import re
import time
import traceback
import uuid

import data_access_token
import folder
import groups
import meta
import schema
from util import avu, collection, config, constants, data_object, group, log, msi, resource, rule, user


def _call_msvc_stat_vault(ctx, resc_name, data_path):
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
    return ctx.msi_json_objops(jsonstr, val, ops)["arguments"][argument_index]


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


def _test_msvc_add_avu_object(ctx):
    tmp_object = _create_tmp_object(ctx)
    ctx.msi_add_avu('-d', tmp_object, "foo", "bar", "baz")
    result = [(m.attr, m.value, m.unit) for m in avu.of_data(ctx, tmp_object)]
    data_object.remove(ctx, tmp_object)
    return result


def _test_msvc_add_avu_collection(ctx):
    tmp_object = _create_tmp_collection(ctx)
    ctx.msi_add_avu('-c', tmp_object, "foo", "bar", "baz")
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_object)]
    collection.remove(ctx, tmp_object)
    return result


def _test_msvc_rmw_avu_object(ctx, rmw_attributes):
    tmp_object = _create_tmp_object(ctx)
    ctx.msi_add_avu('-d', tmp_object, "foo", "bar", "baz")
    ctx.msi_add_avu('-d', tmp_object, "foot", "hand", "head")
    ctx.msi_add_avu('-d', tmp_object, "aap", "noot", "mies")
    ctx.msi_rmw_avu('-d', tmp_object, rmw_attributes[0], rmw_attributes[1], rmw_attributes[2])
    result = [(m.attr, m.value, m.unit) for m in avu.of_data(ctx, tmp_object)]
    data_object.remove(ctx, tmp_object)
    return result


def _test_msvc_rmw_avu_collection(ctx, rmw_attributes):
    tmp_object = _create_tmp_collection(ctx)
    ctx.msi_add_avu('-c', tmp_object, "foo", "bar", "baz")
    ctx.msi_add_avu('-c', tmp_object, "foot", "hand", "head")
    ctx.msi_add_avu('-c', tmp_object, "aap", "noot", "mies")
    ctx.msi_rmw_avu('-c', tmp_object, rmw_attributes[0], rmw_attributes[1], rmw_attributes[2])
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_object)]
    collection.remove(ctx, tmp_object)
    return result


def _test_avu_set_collection(ctx, catch):
    # Test setting avu with catch and without catch
    tmp_object = _create_tmp_collection(ctx)
    avu.set_on_coll(ctx, tmp_object, "foo", "bar", catch)
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_object)]
    collection.remove(ctx, tmp_object)
    return result


def _test_avu_rmw_collection(ctx, rmw_attributes):
    # Test removing with catch and without catch
    tmp_object = _create_tmp_collection(ctx)
    ctx.msi_add_avu('-c', tmp_object, "foo", "bar", "baz")
    ctx.msi_add_avu('-c', tmp_object, "aap", "noot", "mies")
    avu.rmw_from_coll(ctx, tmp_object, rmw_attributes[0], rmw_attributes[1], rmw_attributes[2], rmw_attributes[3])
    result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, tmp_object)]
    collection.remove(ctx, tmp_object)
    return result


def _test_folder_set_retry_avus(ctx):
    tmp_coll = _create_tmp_collection(ctx)
    folder.folder_secure_set_retry_avus(ctx, tmp_coll, 2)
    # Needed to be able to delete collection
    msi.set_acl(ctx, "default", "admin:own", user.full_name(ctx), tmp_coll)
    collection.remove(ctx, tmp_coll)
    return True


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


def _test_groups_data(ctx):
    test_vaultgroup = "vault-default-3"
    ctx.msi_add_avu('-u', test_vaultgroup, "schema_id", "default-3", "")
    groups_data = groups.internal_api_group_data(ctx)
    avu.rmw_from_group(ctx, test_vaultgroup, "schema_id", "default-3", "")
    group_names = [group
                   for catdata in groups_data['group_hierarchy'].values()
                   for subcatdata in catdata.values()
                   for group in subcatdata]
    # We are checking here that the function still works if we have a
    # vault group with a group attribute, that the vault group is not
    # returned (since vault groups are not managed via the group manager
    # module), and that data is returned for group manager managed groups.
    return ("research-default-3" in group_names
            and "datarequests-research-datamanagers" in group_names
            and "grp-vault-test" in group_names
            and "intake-test2" in group_names
            and "deposit-pilot" in group_names
            and "datamanager-test-automation" in group_names
            and "vault-default-3" not in group_names)


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
    ctx.uuGroupAdd("vault-without-research", "test-automation", "something", "", "", "", "", "", "", "")
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


basic_integration_tests = [
    {"name": "msvc.add_avu_collection",
     "test": lambda ctx: _test_msvc_add_avu_collection(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x and len(x) == 1)},
    {"name": "msvc.add_avu_object",
     "test": lambda ctx: _test_msvc_add_avu_object(ctx),
     "check": lambda x: (("foo", "bar", "baz") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
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
     "test": lambda ctx: _call_msvc_json_objops(ctx, '', msi.kvpair(ctx, "e", "f"), 'add',  0),
     "check": lambda x: x == '{"e": "f"}'},
    {"name": "msvc.json_objops.add_notexist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "f"), 'add',  0),
     "check": lambda x: x == '{"a": "b", "e": "f"}'},
    {"name": "msvc.json_objops.add_exist_nonempty",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b"}', msi.kvpair(ctx, "e", "g"), 'add',  0),
     "check": lambda x: x == '{"a": "b", "e": "g"}'},
    {"name": "msvc.json_objops.get_exist",
     "test": lambda ctx: _call_msvc_json_objops(ctx, '{"a": "b", "c": "d"}', msi.kvpair(ctx, "c", ""), 'get',  1),
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
     "check": lambda x: len(x) == len([entry for entry in os.listdir("/var/lib/irods/Vault1_1/yoda") if os.path.isdir("/var/lib/irods/Vault1_1/yoda/" + entry)])},
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
    {"name": "msvc.rmw_avu_collection_literal",
     "test": lambda ctx: _test_msvc_rmw_avu_collection(ctx, ("foo", "bar", "baz")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and ("foot", "hand", "head") in x
                         and len(x) == 2)},
    {"name": "msvc.rmw_avu_object_literal",
     "test": lambda ctx: _test_msvc_rmw_avu_object(ctx, ("foo", "bar", "baz")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and ("foot", "hand", "head") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 2
                         )},
    {"name": "msvc.rmw_avu_collection_literal_notexist",
     "test": lambda ctx: _test_msvc_rmw_avu_collection(ctx, ("does", "not", "exist")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and ("foo", "bar", "baz") in x
                         and ("foot", "hand", "head") in x
                         and len(x) == 3)},
    {"name": "msvc.rmw_avu_object_literal_notexist",
     "test": lambda ctx: _test_msvc_rmw_avu_object(ctx, ("does", "not", "exist")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and ("foo", "bar", "baz") in x
                         and ("foot", "hand", "head") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 3
                         )},
    {"name": "msvc.rmw_avu_collection_wildcard",
     "test": lambda ctx: _test_msvc_rmw_avu_collection(ctx, ("fo%", "%", "%")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and len(x) == 1)},
    {"name": "msvc.rmw_avu_object_wildcard",
     "test": lambda ctx: _test_msvc_rmw_avu_object(ctx, ("fo%", "%", "%")),
     "check": lambda x: (("aap", "noot", "mies") in x
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
     "test": lambda ctx: _test_avu_rmw_collection(ctx, ("foo", "%", True, "%")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "avu.rmw_from_coll_wildcard.catch.no",
     "test": lambda ctx: _test_avu_rmw_collection(ctx, ("foo", "%", False, "%")),
     "check": lambda x: (("aap", "noot", "mies") in x
                         and len([a for a in x if a[0] not in ["org_replication_scheduled"]]) == 1
                         )},
    {"name": "data_access_token.get_all_tokens",
     "test": lambda ctx: data_access_token.get_all_tokens(ctx),
     "check": lambda x: isinstance(x, list)},
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
     "check": lambda x: re.match("^\/tempZone\/home\/vault-initial\/testdata\[[0-9]*\]$", x) is not None},
    {"name":  "folder.determine_new_vault_target.deposit",
     "test": lambda ctx: folder.determine_new_vault_target(ctx, "/tempZone/home/deposit-pilot/deposit-hi[123123]"),
     "check": lambda x: re.match("^\/tempZone\/home\/vault-pilot\/deposit-hi\[[0-9]*\]\[[0-9]*\]$", x) is not None},
    {"name":  "folder.determine_new_vault_target.invalid",
     "test": lambda ctx: folder.determine_new_vault_target(ctx, "/tempZone/home/not-research-group-not-exist/folder-not-exist"),
     "check": lambda x: x == ""},
    {"name":  "groups.getGroupsData",
     "test": lambda ctx: _test_groups_data(ctx),
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
    {"name":  "util.collection.exists.yes",
     "test": lambda ctx: collection.exists(ctx, "/tempZone/yoda"),
     "check": lambda x: x},
    {"name":   "util.collection.exists.no",
     "test": lambda ctx: collection.exists(ctx, "/tempZone/chewbacca"),
     "check": lambda x: not x},
    {"name":   "util.collection.owner",
     "test": lambda ctx: collection.owner(ctx, "/tempZone/yoda"),
     "check": lambda x: x == ('rods', 'tempZone')},
    {"name":   "util.collection.to_from_id",
     "test": lambda ctx: collection.name_from_id(ctx, collection.id_from_name(ctx, "/tempZone/home/research-initial")),
     "check": lambda x: x == "/tempZone/home/research-initial"},
    {"name":   "util.data_object.exists.yes",
     "test": lambda ctx: data_object.exists(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x},
    {"name":   "util.data_object.exists.no",
     "test": lambda ctx: data_object.exists(ctx, "/tempZone/home/research-initial/testdata/doesnotexist.txt"),
     "check": lambda x: not x},
    {"name":   "util.data_object.get_properties.default_properties",
     "test": lambda ctx: data_object.get_properties(ctx, 12188, "irodsResc"),
     "check": lambda x: x["DATA_NAME"] == "lorem.txt"},
    {"name":   "util.data_object.get_properties.no_data_object",
     "test": lambda ctx: data_object.get_properties(ctx, 1218812188, "irodsResc"),
     "check": lambda x: x["DATA_SIZE"] is None},
    {"name":   "util.data_object.owner",
     "test": lambda ctx: data_object.owner(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == ('rods', 'tempZone')},
    {"name":   "util.data_object.size",
     "test": lambda ctx: data_object.size(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == 1003240},
    {"name":   "util.data_object.get_group_owners",
     "test": lambda ctx: data_object.get_group_owners(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == [['research-initial', 'tempZone']]},
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
     "check": lambda x: sorted([member for member in x]) == sorted([('functionaladminpriv', 'tempZone'), ('functionaladminpriv@yoda.test', 'tempZone'), ('groupmanager', 'tempZone'), ('groupmanager@yoda.test', 'tempZone'), ('researcher', 'tempZone'), ('researcher@yoda.test', 'tempZone')])},
    {"name":   "util.group.members.doesnotexist",
     "test": lambda ctx: user.exists(ctx, "research-doesnotexist"),
     "check": lambda x: x is False},
    {"name":   "util.resource.exists.yes",
     "test": lambda ctx: resource.exists(ctx, "irodsResc"),
     "check": lambda x: x},
    {"name":   "util.resource.exists.no",
     "test": lambda ctx: resource.exists(ctx, "bananaResc"),
     "check": lambda x: not x},
    {"name":   "util.resource.get_all_resource_names",
     "test": lambda ctx: resource.get_all_resource_names(ctx),
     "check": lambda x: len(x) == 16},
    {"name":   "util.resource.get_children_by_name",
     "test": lambda ctx: resource.get_children_by_name(ctx, "dev001_p1"),
     "check": lambda x: x == ["dev001_1"]},
    {"name":   "util.resource.get_parent_by_name",
     "test": lambda ctx: resource.get_parent_by_name(ctx, "dev001_1"),
     "check": lambda x: x == "dev001_p1"},
    {"name":   "util.resource.get_resource_names_by_type",
     "test": lambda ctx: resource.get_resource_names_by_type(ctx, "unixfilesystem"),
     "check": lambda x: sorted(x) == sorted(['bundleResc', 'demoResc', 'dev001_1', 'dev001_2', 'dev002_1'])},
    {"name":   "util.resource.get_type_by_name",
     "test": lambda ctx: resource.get_type_by_name(ctx, "dev001_1"),
     "check": lambda x: x == "unixfilesystem"},
    {"name":   "util.resource.to_from_id",
     "test": lambda ctx: resource.name_from_id(ctx, resource.id_from_name(ctx, "irodsResc")),
     "check": lambda x: x == "irodsResc"},
    {"name":   "util.user.exists.yes",
     "test": lambda ctx: user.exists(ctx, "rods"),
     "check": lambda x: x},
    {"name":   "util.user.exists.no",
     "test": lambda ctx: user.exists(ctx, "rododendron"),
     "check": lambda x: not x},
    {"name":   "util.user.is_admin.yes",
     "test": lambda ctx: user.is_admin(ctx, "rods"),
     "check": lambda x: x},
    {"name":   "util.user.is_admin.no",
     "test": lambda ctx: user.is_admin(ctx, "researcher"),
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
    {"name":   "util.user.usertype.rodsadmin",
     "test": lambda ctx: user.user_type(ctx, "rods"),
     "check": lambda x: x == "rodsadmin"},
    {"name":   "util.user.usertype.rodsuser",
     "test": lambda ctx: user.user_type(ctx, "researcher"),
     "check": lambda x: x == "rodsuser"},
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

    return_value = ""
    log.write(ctx, "Running")

    if config.environment != "development":
        log.write(ctx, "Error: integration tests can only run on development environment.")
        return ""

    if user.user_type(ctx) != 'rodsadmin':
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
        elif check(result):
            verdict = "VERDICT_OK       "
        else:
            verdict = "VERDICT_FAILED   (output '{}')".format(str(result))

        return_value += name + " " + verdict + "\n"

    return return_value


def _call_file_checksum_either_resc(ctx, filename):
    """Returns result of file checksum microservice for either of the
       two main UFS resources (dev001_1, dev001_2). If one returns an
       exception, we try the other.

       :param ctx: combined type of a callback and rei struct
       :param filename: name of file to checksum

       :returns: output of file checksum microservice
    """
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
    ret = msi.dir_list(ctx, dirname, resc_name, "")
    print(ret['arguments'][2])
    return json.loads(ret['arguments'][2])


def _call_dir_list_check_exc(ctx, dirname, resc_name):
    try:
        msi.dir_list(ctx, dirname, resc_name, "")
        return False
    except Exception:
        return True
