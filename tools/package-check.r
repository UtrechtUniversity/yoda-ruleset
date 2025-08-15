#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/package-check.r '*coll=' '*mode='
#
import genquery
import os


# Determine existence of collection
def coll_exists(coll, ctx):
    exists_query = genquery.row_iterator(
        "COLL_ID",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    if exists_query.total_rows() > 0:
        return True
    else:
        return False


# Get user name from user ID
def get_user_name(id, ctx):
    user_query = genquery.row_iterator(
        "USER_NAME",
        "USER_ID = '{}'".format(id),
        genquery.AS_LIST,
        ctx)

    user_name = ""
    if user_query.total_rows() > 0:
        for result in user_query:
            user_name = result[0]
    return user_name


# Get group collection
def get_group_coll(coll, ctx):
    group_coll = ""
    if coll.rsplit('/', 1)[-1].startswith("vault-"):
        group_coll = coll
    else:
        group_query = genquery.row_iterator(
            "COLL_PARENT_NAME",
            "COLL_NAME like '{}'".format(coll),
            genquery.AS_LIST,
            ctx)

        if group_query.total_rows() > 0:
            for result in group_query:
                if result[0].rsplit('/', 1)[-1].startswith("vault-"):
                    group_coll = result[0]
                else:   # If parent collection is not group collection, go up another level
                    group_coll = get_group_coll(group_coll, ctx)
    return group_coll


# Get AVUs from collection
def get_avus(coll, avu, ctx):
    avu_query = genquery.row_iterator(
        "ORDER(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '{}' AND COLL_NAME = '{}'".format(avu, coll),
        genquery.AS_LIST,
        ctx)

    avus = {}
    if avu_query.total_rows() > 0:
        for (attribute, value) in avu_query:
            avus[attribute] = value
    return avus


# Get collection's subcollections
def get_subcolls(coll, ctx):
    subcoll_query = genquery.row_iterator(
            "COLL_NAME",
            "COLL_NAME like '{}/%'".format(coll),
            genquery.AS_LIST,
            ctx)

    subcolls = []
    if subcoll_query.total_rows() > 0:
        for result in subcoll_query:
            subcolls.append(result[0])
        
    return subcolls


# Get collection's data objects
def get_dataobjs(coll, ctx):
    data_query = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    dataobjs = []
    if data_query.total_rows() > 0:
        for result in data_query:
            dataobjs.append(result[0])

    return dataobjs            


# Get ACLs of collection
def get_coll_acls(coll, ctx):
    access_query = genquery.row_iterator(
        "ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    acl = []
    if access_query.total_rows() > 0:
        for (user, access) in access_query:
            user_access = {}

            user_access['user_id'] = user
            user_access['user_name'] = get_user_name(user, ctx)
    
            if access == "read_object":
                user_access['access'] = "read"
            elif access == "modify_object":
                user_access['access'] = "write"
            else:
                user_access['access'] = access
    

            acl.append(user_access)
        # for item in acl:
        #     for key, value in item.items():
        #         ctx.writeLine("stdout", "{}, {}".format(key, value))
    return acl


# Get ACLs of data
def get_data_acls(coll, data, ctx):
    access_query = genquery.row_iterator(
        "ORDER(DATA_ACCESS_USER_ID), DATA_ACCESS_NAME",
        "COLL_NAME like '{}' AND DATA_NAME like '{}'".format(coll, data),
        genquery.AS_LIST,
        ctx)

    acl = []
    if access_query.total_rows() > 0:    
        for (user, access) in access_query:
            user_access = {}

            user_access['user_id'] = user
            user_access['user_name'] = get_user_name(user, ctx)

            if access == "read_object":
                user_access['access'] = "read"
            elif access == "modify_object":
                user_access['access'] = "write"
            else:
                user_access['access'] = access
    

            acl.append(user_access)

        # for item in acl:
        #     for key, value in item.items():
        #         ctx.writeLine("stdout", "{}, {}".format(key, value))
    return acl


# Compare ACLs
def compare_acls(acls, g_acls, path, mode, ctx):
    if len(g_acls) > 0 and len(acls) > 0:
        if (acls == g_acls): # TODO: ensure check makes sense?
            ctx.writeLine("stdout", "OK: ACLs of current collection/data object match group ACLs. (Path: {})".format(path))
        else:
            ctx.writeLine("stdout", "WARN: ACLs of current collection/data object do not match group ACLs. (Path: {})".format(path))

            acls_to_remove = []
            acls_to_add = []            
            for acl in acls + g_acls:
                if acl not in acls:
                    ctx.writeLine("stdout", "\tUser '{}' has '{}' rights to group collection, but not to this collection/data object.".format(acl['user_name'], acl['access']))
                    acls_to_add.append(acl)
                elif acl not in g_acls:
                    ctx.writeLine("stdout", "\tUser '{}' has '{}' rights to this collection/data object, but not to group collection.".format(acl['user_name'], acl['access']))
                    acls_to_remove.append(acl)
            
            if mode == "write":
                if len(acls_to_add) > 0:
                    ctx.writeLine("stdout", "\tRunning in {} mode, adding missing ACLs...".format(mode))
                    
                    for acl in acls_to_add:
                        try:
                            ctx.msiSetACL("default", "admin:" + str(access), str(user_name), str(path))
                        except Exception:
                            ctx.writeString("serverLog", "Something went wrong while setting ACL.")
                    
                if len(acls_to_remove) > 0:
                    ctx.writeLine("stdout", "\tRunning in {} mode, removing extra ACLs...".format(mode))
                    
                    for acl in acls_to_remove:
                        user_name = acl['user_name']
                        access = acl['access']

                        if user_name == "rods" or user_name == "anonymous":
                            ctx.writeLine("stdout", "\tUser is '{}', skipping...".format(user_name))
                        else:                        
                            try: 
                                ctx.msiSetACL("default", "null", str(acl['user_name']), str(path))
                            except Exception:
                                ctx.writeString("serverLog", "Something went wrong while setting ACL.")                    
    else:
        ctx.writeLine("stdout", "ERROR: No ACLs found for this collection/data object. (Path: {})".format(path))


# Check inheritance of collection
def check_coll_inheritance(coll, mode, ctx):
    inherit_query = genquery.row_iterator(
        "COLL_INHERITANCE",
        "COLL_NAME like '{}'".format(coll),
        genquery.AS_LIST,
        ctx)

    inheritance = ""
    if inherit_query.total_rows() > 0:
        for result in inherit_query:
            inheritance = "Disabled" if result[0] == "0" else "Enabled"
    
    if inheritance == "Disabled":
        ctx.writeLine("stdout", "OK: Inheritance is {}. (Collection: {})".format(inheritance, coll))
    elif inheritance == "Enabled":
        ctx.writeLine("stdout", "WARN: inheritance is {}, should be Disabled. (Collection: {})".format(inheritance, coll))

        if mode == "write":
            ctx.writeLine("stdout", "Running in {} mode, fixing...".format(mode))

            try:
                ctx.msiSetACL("recursive", "admin:noinherit", "", str(coll))
            except Exception:
                ctx.writeString("serverLog", "Something went wrong while setting inheritance.")
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve collection's inheritance. (Collection: {})".format(coll))


# Check ACLs
def check_acls(coll, mode, ctx):
    # Get group collection
    group_coll = get_group_coll(coll, ctx)

    if group_coll != "": 
        # Check ACLs of provided collection
        group_acls = get_coll_acls(group_coll, ctx)
        coll_acls = get_coll_acls(coll, ctx)
        compare_acls(coll_acls, group_acls, coll, mode, ctx)

        # Check ACLs of provided collection's data objects
        dataobjs = get_dataobjs(coll, ctx)

        if len(dataobjs) > 0:
            for data_obj in dataobjs:
                dataobj_acls = get_data_acls(coll, data_obj, ctx)
                compare_acls(dataobj_acls, group_acls, "{}/{}".format(coll, data_obj), mode, ctx)             

        # Check ACLs of provided collection's subcollections
        subcolls = get_subcolls(coll, ctx)

        if len(subcolls) > 0:
            for subcoll in subcolls:
                subcoll_acls = get_coll_acls(subcoll, ctx)
                compare_acls(subcoll_acls, group_acls, subcoll, mode, ctx)
        
            # Check ACLs of provided collection's subcollections' data objects
            subcoll_dataobjs = get_dataobjs(subcoll, ctx)
            
            if len(subcoll_dataobjs) > 0:
                for subcoll_dataobj in subcoll_dataobjs:
                    subcoll_dataobj_acls = get_data_acls(subcoll, subcoll_dataobj, ctx)
                    compare_acls(subcoll_dataobj_acls, group_acls, "{}/{}".format(subcoll, subcoll_dataobj), mode, ctx)
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve group collection.")          


# Check inheritance
def check_inheritance(coll, mode, ctx):
    # Inheritance should be disabled on vault packages
    # Check inheritance of collection
    coll_inherit = check_coll_inheritance(coll, mode, ctx)

    # Check inheritance of collection's subcollections
    subcolls = get_subcolls(coll, ctx)

    if len(subcolls) > 0:
        for subcoll in subcolls:
            subcoll_inherit = check_coll_inheritance(subcoll, mode, ctx)


def check_metadata(coll, mode, user, ctx):
    # if vault status "PUBLISHED" or "DEPUBLISHED"
        # if AVU refers to Yoda collection, update zone name
        # if DOI record exists at DataCite, update URL
        # call update-publications.r on package

    coll_avus = get_avus(coll, "org_%", ctx)

    if bool(coll_avus):
        vault_status = coll_avus['org_vault_status']
        if vault_status == "PUBLISHED" or vault_status == "DEPUBLISHED":
            for (attr, value) in coll_avus.items():
                if os.path.isabs(value):
                    current_zone = ctx.uuClientZone("")['arguments'][0]
                    avu_zone = value.split('/')[1]
                    if avu_zone != current_zone:
                        ctx.writeLine("stdout", "WARN: AVU '{}' contains zone that does not match current zone. (AVU zone: '{}', current zone: '{}')".format(attr, avu_zone, current_zone))

                        if (mode == "write"):
                            ctx.writeLine("stdout", "Running in {} mode, fixing...".format(mode))
                            # ctx.writeLine("stdout", "...Done.")

                    else:
                        ctx.writeLine("stdout", "OK: AVU '{}' contains zone that matches current zone. (AVU zone: '{}', current zone: '{}')".format(attr, avu_zone, current_zone))

                        # TODO: move this to the other check once done testing
                        ctx.writeLine("stdout", "Old value: {}".format(value))
                        if (mode == "write"):
                            ctx.writeLine("stdout", "Running in {} mode, fixing...".format(mode))
                            new_value = value.replace(avu_zone, "newZone")
                            ctx.writeLine("stdout", "New value: {}".format(new_value))

                            try:
                                # Set write permissions first to be able to modify AVU
                                ctx.msiSetACL("recursive", "admin:write", str(user), str(coll))

                                # Update zone
                                out = ctx.msiString2KeyValPair("{}={}".format(str(attr), str(new_value)), 0)
                                kvp = out['arguments'][1]
                                ctx.msiSetKeyValuePairsToObj(kvp, coll, '-C')
                                
                                # Remove write permissions
                                ctx.msiSetACL("recursive", "null", str(user), str(coll))                        

                            except Exception:
                                ctx.writeLine("stdout", "Something went wrong while setting AVU.")
                                # ctx.writeString("serverLog", "Something went wrong while setting AVU.")


def main(rule_args, ctx, rei):
    coll = global_vars["*coll"]
    mode = global_vars["*mode"]
    
    try:
        current_user = ctx.uuClientFullNameWrapper("")['arguments'][0]
        current_user_type = ctx.uuGetUserType(current_user, "")['arguments'][1]
    except Exception:
        ctx.writeString("serverLog", "Something went wrong while retrieving user information.")

    if current_user_type == 'rodsadmin':    
        if coll_exists(coll,ctx):
            if 'vault-' in coll:
                ctx.writeLine("stdout", "Executing package check rule for collection: {} (mode: {})".format(coll, mode))
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Check if collection ACLs match group ACLs
                check_acls(coll, mode, ctx)
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Check collection inheritance        
                check_inheritance(coll, mode, ctx)
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Update metadata
                check_metadata(coll, mode, current_user, ctx)            
            else:
                ctx.writeLine("stdout", "ERROR: This rule should be run on vault collections only.")
        else:
            ctx.writeLine("stdout", "ERROR: Collection does not exist, try again.")
    else:
        ctx.writeLine("stdout", "ERROR: This rule can only be run by a rodsadmin user.")    

INPUT *coll=, *mode=read
OUTPUT ruleExecOut

# TODO: Test another user
# TODO: Add sanity check (double check ACLs for specific users)
# TODO: Add sanity check (rerun check after fix)
# (DONE) TODO: Add a check so that it only runs on vault packages
# TODO: Reorder arguments so that ctx is always the first argument (similar to the ruleset), except for main
# TODO: Use the same docstyle (Sphinx) for function comments
# TODO: Run flake8 / ruff on the script for linting