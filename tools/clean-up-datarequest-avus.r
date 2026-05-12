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


# Remove all obsolete datarequest AVUs in the current zone
def remove_obsolete_avus(ctx, zone, dryrun):
    query = genquery.Query(ctx,
                           "COLL_NAME, DATA_NAME, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
                           f"COLL_NAME like '/{zone}/home/datarequests%' AND DATA_NAME like '%datarequest%'")

    count = 0
    found_any = False
    for row in query:
        found_any = True
        coll, obj, attr, value = row[0], row[1], row[2], row[3]
        if attr not in VALID_AVUS:
            ctx.writeLine("stdout", f"Obsolete AVU found for object {coll}/{obj}: attribute '{attr}' with value '{value}'")
            count += 1

            if not dryrun:
                ctx.writeLine("stdout", "Deleting...")
                msi.mod_avu_metadata(ctx, "-d", f"{coll}/{obj}", "rm", attr, value, "")

    if not found_any:
        ctx.writeLine("stdout", "No data request object was found in the current zone.")
        return

    if count > 0 and not dryrun:
        ctx.writeLine("stdout", "Done.")
    elif count > 0 and dryrun:
        ctx.writeLine("stdout", "Run in exec mode to delete these obsolete AVUs.")
    else:
        ctx.writeLine("stdout", "No obsolete data request AVU found in the current zone.")


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

    # Remove all obsolete AVUs in the zone
    if dryrun:
        ctx.writeLine("stdout", "Running in dry-run mode... AVUs will not be deleted.")

    remove_obsolete_avus(ctx, current_zone, dryrun)

INPUT *mode=dry
OUTPUT ruleExecOut