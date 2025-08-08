#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/package-check.r '*coll=' '*mode='
#
import genquery

# TODO: check that parent folder includes words like "vault"?
def get_coll_parent(coll, ctx):
    parent_query = genquery.row_iterator(
        "COLL_PARENT_NAME",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)
	
    for parent in parent_query:
        try: 
            return parent[0]
        except Exception:
            ctx.writeString("queryError", "Error retrieving parent collection of data package {}".format(coll))

def get_coll_access(coll, ctx):
    ctx.writeLine("stdout", "Retrieving ACLs of data package {}".format(coll)) 
    access_query = genquery.row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
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

    for item in acl:
        for key, value in item.items():
            ctx.writeLine("stdout", "{}, {}".format(key, value))    

    return acl

def get_coll_inheritance(coll, ctx):
    inherit_query = genquery.row_iterator(
        "COLL_INHERITANCE",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)
	
    for inherit in inherit_query:
        try: 
            return inherit[0]
        except Exception:
            ctx.writeString("queryError", "Error retrieving inheritance info of data package {}".format(coll))

def main(rule_args, ctx, rei):
    coll = global_vars["*coll"]
    mode = global_vars["*mode"]

    parent_coll = get_coll_parent(coll, ctx)

    coll_acl = get_coll_access(coll, ctx)
    parent_acl = get_coll_access(parent_coll, ctx)

    coll_inherit = get_coll_inheritance(coll, ctx)
    parent_inherit = get_coll_inheritance(parent_coll, ctx)

    if (coll_acl == parent_acl):
        ctx.writeLine("stdout", "Data package ACLs match group ACLs.") # TODO: ensure check makes sense?    

    if (coll_inherit == parent_inherit):
        ctx.writeLine("stdout", "Data package inheritance matches group inheritance.") # TODO: this check or just "if package is in vault then must be disabled"?

INPUT *coll=, *mode=read
OUTPUT ruleExecOut