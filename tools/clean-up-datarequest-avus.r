#!/usr/bin/env python3

"""Clean up obsolete AVUs from data request module data objects."""

# !/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Clean up obsolete AVUs from data request module data objects.
#
# Usage:
# $ irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/clean-up-datarequest-avus.r '*mode=exec/dry'
#
# *mode: Script mode of execution (exec = executes commands, dry = print out commands instead)
#

import genquery

import msi

VALID_AVUS = ['assignedForReview', 'endOfReviewPeriod', 'owner', 'reviewedBy', 'status', 'title']  # List of valid datarequest AVUs


# Get all datarequest data objects in the current zone
def get_datarequest_objs(ctx, zone):
    iter = genquery.Query(ctx,
                          "COLL_NAME, DATA_NAME",
                          f"COLL_NAME like '/{zone}/home/datarequest%'")

    datarequest_objs = []
    for row in iter:
        if row[1] == "datarequest.json":
            datarequest_objs.append((row[0], row[1]))

    return datarequest_objs


# Remove obsolete datarequest AVUs
def remove_obsolete_avus(ctx, obj, dryrun):
    iter = genquery.Query(ctx,
                          "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
                          f"COLL_NAME = '{obj[0]}' AND DATA_NAME = '{obj[1]}'")

    for row in iter:
        if row[0] not in VALID_AVUS:
            ctx.writeLine("stdout", f"Obsolete AVU found for object {obj[0]}/{obj[1]}: attribute '{row[0]}' with value '{row[1]}'")

            if not dryrun:
                ctx.writeLine("stdout", "Deleting...")
                msi.mod_avu_metadata(ctx, "-d", f"{obj[0]}/{obj[1]}", "rm", row[0], row[1], "")


def main(rule_args, ctx, rei):
    mode = global_vars["*mode"].strip('"')

    # Evaluate mode of execution
    if mode == "dry":
        dryrun = True
    elif mode == "exec":
        dryrun = False
    else:
        ctx.writeLine("stdout", "ERROR: Script modes can only be 'exec' or 'dry'.")
        return

    # Get client information
    try:
        current_user = ctx.uuClientFullNameWrapper("")['arguments'][0]
        current_user_type = ctx.uuGetUserType(current_user, "")['arguments'][1]
        current_zone = ctx.uuClientZone("")['arguments'][0]
    except Exception:
        ctx.writeLine("stdout", "ERROR: Could not retrieve client information.")
        return

    # Check if user is rodsadmin
    if current_user_type != 'rodsadmin':
        ctx.writeLine("stdout", "ERROR: This rule can only be run by a rodsadmin user.")
        return

    # Get all data request data objects
    if dryrun:
        ctx.writeLine("stdout", "Running in dry-run mode... AVUs will not be deleted.")

    datarequest_objs = get_datarequest_objs(ctx, current_zone)
    if not datarequest_objs:
        ctx.writeLine("stdout", "No data request data object was found.")
        return
    else:
        for obj in datarequest_objs:
            remove_obsolete_avus(ctx, obj, dryrun)

INPUT *mode=dry
OUTPUT ruleExecOut