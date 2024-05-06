# -*- coding: utf-8 -*-
"""Integration tests for the development environment."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_run_integration_tests']

import json
import os
import traceback

from util import collection, config, data_object, log, msi, resource, rule, user


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
    {"name":   "util.data_object.owner",
     "test": lambda ctx: data_object.owner(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == ('rods', 'tempZone')},
    {"name":   "util.data_object.size",
     "test": lambda ctx: data_object.size(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == 1003240},
    {"name":   "util.data_object.get_group_owners",
     "test": lambda ctx: data_object.get_group_owners(ctx, "/tempZone/home/research-initial/testdata/lorem.txt"),
     "check": lambda x: x == [['research-initial', 'tempZone']]},
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
    {"name":   "util.user.usertype.rodsadmin",
     "test": lambda ctx: user.user_type(ctx, "rods"),
     "check": lambda x: x == "rodsadmin"},
    {"name":   "util.user.usertype.rodsuser",
     "test": lambda ctx: user.user_type(ctx, "researcher"),
     "check": lambda x: x == "rodsuser"},
]


@rule.make(inputs=[], outputs=[0])
def rule_run_integration_tests(ctx):
    """This function runs the integration tests. It must be run by
    a rodsadmin user on a development environment. It assumes the standard
    test data is present.

    :param ctx:  Combined type of a callback and rei struct

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
