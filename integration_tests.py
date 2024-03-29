# -*- coding: utf-8 -*-
"""Integration tests for the development environment."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_run_integration_tests']

import traceback

from util import collection, config, data_object, log, resource, rule, user

basic_integration_tests = [
    {"name":   "util.collection.exists.yes",
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
