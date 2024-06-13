# -*- coding: utf-8 -*-
"""Integration tests for the development environment."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_run_integration_tests']

import traceback
import uuid

from util import avu, collection, config, data_object, log, msi, resource, rule, user


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
    {"name": "policies.check_anonymous_access_allowed.local",
     "test": lambda ctx: ctx.rule_check_anonymous_access_allowed("127.0.0.1", ""),
     "check": lambda x: x['arguments'][1] == 'true'},
    {"name": "policies.check_anonymous_access_allowed.remote",
     "test": lambda ctx: ctx.rule_check_anonymous_access_allowed("1.2.3.4", ""),
     "check": lambda x: x['arguments'][1] == 'false'},
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
