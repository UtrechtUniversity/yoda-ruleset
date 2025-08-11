#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/package-check.r '*coll=' '*mode='
#
import genquery


# Determine existence of collection
def coll_exists(coll, ctx):
    try:
        exists_query = genquery.row_iterator(
            "COLL_ID",
            "COLL_NAME like '{}'".format(coll),
            genquery.AS_LIST,
            ctx)

        if exists_query.total_rows() > 0:
            return True
        else:
            return False

    except Exception:
        ctx.writeString("queryError", "Error determining existence of data package {}".format(coll))


# Get parent of collection
def get_coll_parent(coll, ctx):
    parent_query = genquery.row_iterator(
        "COLL_PARENT_NAME",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    for result in parent_query:
        try:
            parent = result[0]
            if 'vault-' in parent: # TODO: check if path ends in "vault-*"
                return parent
        except Exception:
            ctx.writeString("queryError", "Error retrieving parent collection of data package {}".format(coll))


# Get ACLs of collection
def get_coll_acls(coll, ctx):
    access_query = genquery.row_iterator(
        "ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    acl = []
    for (user, access) in access_query:
        try:
            user_access = {}

            user_access['user'] = user
            user_access['access'] = access

            acl.append(user_access)
        except Exception:
            ctx.writeString("queryError", "Error retrieving ACLs of data package {}".format(coll))

    # for item in acl:
    #     for key, value in item.items():
    #         ctx.writeLine("stdout", "{}, {}".format(key, value))

    return acl


# Get inheritance of collection
def get_coll_inheritance(coll, ctx):
    inherit_query = genquery.row_iterator(
        "COLL_INHERITANCE",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    for result in inherit_query:
        try:
            inheritance = "Disabled" if result[0] == "0" else "Enabled"
            return inheritance
        except Exception:
            ctx.writeString("queryError", "Error retrieving inheritance info of data package {}".format(coll))


def main(rule_args, ctx, rei):
    coll = global_vars["*coll"]
    mode = global_vars["*mode"]

    # TODO: check if user running script is rodsadmin

    if coll_exists(coll, ctx):
        parent_coll = get_coll_parent(coll, ctx)

        coll_acl = get_coll_acls(coll, ctx)
        parent_acl = get_coll_acls(parent_coll, ctx)

        coll_inherit = get_coll_inheritance(coll, ctx)
        parent_inherit = get_coll_inheritance(parent_coll, ctx)

        # Check if data packge ACLs match group ACLs
        if (coll_acl == parent_acl):
            ctx.writeLine("stdout", "Data package ACLs match group ACLs.") # TODO: ensure check makes sense?
        else:
            ctx.writeLine("stdout", "Data package ACLs do NOT match group ACLs.")
            # TODO: show ACLs that need fixing

            if mode == "write":
                ctx.writeLine("stdout", "Fixing...")

        # Check if data packge inheritance matches group inheritance            
        if (coll_inherit == parent_inherit): # TODO: this check or just "if package is in vault then must be disabled"?
            ctx.writeLine("stdout", "Data package inheritance matches group inheritance.")
        else:
            ctx.writeLine("stdout", "Data package inheritance does NOT match group inheritance.")
            # TODO: show inheritance differences

            if mode == "write":
                ctx.writeLine("stdout", "Fixing...")                
    else:
        ctx.writeLine("stdout", "Collection does not exist, try again.")

INPUT *coll=, *mode=read
OUTPUT ruleExecOut