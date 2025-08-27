#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Checks data package for incorrect ACLs and/or AVUs after migration.
#
# Usage:
# $ irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/package-check.r '*coll=/example/package' '*mode=read/write'
#
# *coll: path of the collection to be checked
# *mode: read (report only), write (report and fix)
#
import os

import genquery


# Determine existence of a collection
def coll_exists(ctx, coll):
    exists_query = genquery.row_iterator(
        "COLL_ID",
        f"COLL_NAME like '{coll}'",
        genquery.AS_LIST,
        ctx)

    if exists_query.total_rows() > 0:
        return True
    else:
        return False


# Get user name from user ID
def get_user_name(ctx, id):
    user_query = genquery.row_iterator(
        "USER_NAME",
        f"USER_ID = '{id}'",
        genquery.AS_LIST,
        ctx)

    user_name = ""
    if user_query.total_rows() > 0:
        for result in user_query:
            user_name = result[0]
    return user_name


# Get group from collection
def get_group_coll(ctx, coll):
    group_coll = ""
    if coll.rsplit('/', 1)[-1].startswith("vault-"):
        group_coll = coll
    else:
        group_query = genquery.row_iterator(
            "COLL_PARENT_NAME",
            f"COLL_NAME like '{coll}'",
            genquery.AS_LIST,
            ctx)

        if group_query.total_rows() > 0:
            for result in group_query:
                if result[0].rsplit('/', 1)[-1].startswith("vault-"):
                    group_coll = result[0]
                else:   # If parent collection is not group collection, go up another level
                    group_coll = get_group_coll(ctx, group_coll)

    return group_coll


# Get AVUs from a collection
def get_avus(ctx, coll, avu):
    avu_query = genquery.row_iterator(
        "ORDER(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE",
        f"META_COLL_ATTR_NAME like '{avu}' AND COLL_NAME = '{coll}'",
        genquery.AS_LIST,
        ctx)

    avus = {}
    if avu_query.total_rows() > 0:
        for (attribute, value) in avu_query:
            avus[attribute] = value
    return avus


# Get subcollections of a collection
def get_subcolls(ctx, coll):
    subcoll_query = genquery.row_iterator(
        "COLL_NAME",
        f"COLL_NAME like '{coll}/%'",
        genquery.AS_LIST,
        ctx)

    subcolls = []
    if subcoll_query.total_rows() > 0:
        for result in subcoll_query:
            subcolls.append(result[0])

    return subcolls


# Get data objects in a collection
def get_dataobjs(ctx, coll):
    data_query = genquery.row_iterator(
        "DATA_NAME",
        f"COLL_NAME like '{coll}'",
        genquery.AS_LIST,
        ctx)

    dataobjs = []
    if data_query.total_rows() > 0:
        for result in data_query:
            dataobjs.append(result[0])

    return dataobjs


# Get ACLs of a collection
def get_coll_acls(ctx, coll):
    access_query = genquery.row_iterator(
        "ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME",
        f"COLL_NAME like '{coll}'",
        genquery.AS_LIST,
        ctx)

    acl = []
    if access_query.total_rows() > 0:
        for (user, access) in access_query:
            user_access = {}

            user_access['user_id'] = user
            user_access['user_name'] = get_user_name(ctx, user)

            if access == "read_object":
                user_access['access'] = "read"
            elif access == "modify_object":
                user_access['access'] = "write"
            else:
                user_access['access'] = access

            acl.append(user_access)

    return acl


# Get ACLs of a data object
def get_data_acls(ctx, coll, data):
    access_query = genquery.row_iterator(
        "ORDER(DATA_ACCESS_USER_ID), DATA_ACCESS_NAME",
        f"COLL_NAME like '{coll}' AND DATA_NAME like '{data}'",
        genquery.AS_LIST,
        ctx)

    acl = []
    if access_query.total_rows() > 0:
        for (user, access) in access_query:
            user_access = {}

            user_access['user_id'] = user
            user_access['user_name'] = get_user_name(ctx, user)

            if access == "read_object":
                user_access['access'] = "read"
            elif access == "modify_object":
                user_access['access'] = "write"
            else:
                user_access['access'] = access

            acl.append(user_access)

    return acl


# Compare ACLs of a collection/data object with group ACLs
def compare_acls(ctx, acls, g_acls, path, mode):
    if len(g_acls) > 0 and len(acls) > 0:
        if (acls == g_acls):
            ctx.writeLine("stdout", f"OK: ACLs of current collection/data object are correct. (Path: {path})")
        else:
            acls_to_remove = []
            acls_to_add = []

            # Join ACLs of both lists
            join_acls = [acl for i, acl in enumerate(acls + g_acls) if acl not in (acls + g_acls)[:i]]
            for acl in join_acls:
                user_name = acl['user_name']
                access = acl['access']

                if acl not in acls:  # If ACL is in group collection's ACLs but not collection/data object's ACLs, it might need to be added
                    if access != "own":  # Any own rights from group collection can be skipped
                        acls_to_add.append(acl)
                elif acl not in g_acls:  # If ACL is in collection/data object's ACLs but not in group collection's ACLs, it might need to be removed
                    if user_name != "rods" and (user_name == "anonymous" and access != "read"):  # If rods has any rights or anonymous has read rights, they don't have to be removed
                        acls_to_remove.append(acl)
                elif user_name in path and access == "own":  # If group already has own rights on collection/data object, they should be removed
                    acls_to_remove.append(acl)

            if len(acls_to_add) > 0 or len(acls_to_remove) > 0:
                ctx.writeLine("stdout", f"WARN: ACLs of current collection/data object have issues. (Path: {path})")

                # Add missing ACLs
                if len(acls_to_add) > 0:
                    for acl in acls_to_add:
                        user_id = acl['user_id']
                        user_name = acl['user_name']
                        access = acl['access']

                        ctx.writeLine("stdout", f"\tUser/group '{user_name}' has '{access}' rights to the group collection but not to this collection/data object, and should have those rights.")

                        if mode == "write":
                            ctx.writeLine("stdout", f"\tRunning in {mode} mode, adding missing ACLs...")
                            try:
                                ctx.msiSetACL("default", "admin:" + str(access), str(user_name), str(path))
                            except Exception:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting ACLs. (Path: {path})")

                            # Ensure write operation was successful
                            if ensure_fix(ctx, "acl-add", path, user_id=user_id, access=access):
                                ctx.writeLine("stdout", "\tDone.")
                            else:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting ACLs. (Path: {path})")

                # Remove extra ACLs
                if len(acls_to_remove) > 0:
                    for acl in acls_to_remove:
                        user_id = acl['user_id']
                        user_name = acl['user_name']
                        access = acl['access']

                        ctx.writeLine("stdout", f"\tUser/group '{user_name}' has '{access}' rights to this collection/data object, but should not have those rights.")

                        if mode == "write":
                            ctx.writeLine("stdout", f"\tRunning in {mode} mode, removing extra ACLs...")
                            try:
                                ctx.msiSetACL("default", "null", str(acl['user_name']), str(path))
                            except Exception:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting ACLs. (Path: {path})")

                            # Ensure write operation was successful
                            if ensure_fix(ctx, "acl-remove", path, user_id=user_id, access=access):
                                ctx.writeLine("stdout", "\tDone.")
                            else:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting ACLs. (Path: {path})")
            else:
                ctx.writeLine("stdout", f"OK: ACLs of current collection/data object are correct. (Path: {path})")
    else:
        ctx.writeLine("stdout", f"ERROR: No ACLs found for this collection/data object. (Path: {path})")


# Check inheritance of a collection
def check_coll_inheritance(ctx, coll, mode):
    inherit_query = genquery.row_iterator(
        "COLL_INHERITANCE",
        f"COLL_NAME like '{coll}'",
        genquery.AS_LIST,
        ctx)

    inheritance = ""
    if inherit_query.total_rows() > 0:
        for result in inherit_query:
            inheritance = "Enabled" if result[0] == "1" else "Disabled"

    # Vault packages should have inheritance disabled
    if inheritance == "Disabled":
        ctx.writeLine("stdout", f"OK: Inheritance is {inheritance}. (Path: {coll})")
    elif inheritance == "Enabled":
        ctx.writeLine("stdout", f"WARN: inheritance is {inheritance}, should be Disabled. (Path: {coll})")

        if mode == "write":
            ctx.writeLine("stdout", f"\tRunning in {mode} mode, fixing...")

            try:
                ctx.msiSetACL("recursive", "admin:noinherit", "", str(coll))
            except Exception:
                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting inheritance. (Path: {coll})")

            # Ensure write operation was successful
            if ensure_fix(ctx, "inheritance", coll):
                ctx.writeLine("stdout", "\tDone.")
            else:
                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting inheritance. (Path: {coll})")
    else:
        ctx.writeLine("stdout", f"ERROR: Could not retrieve collection's inheritance. (Path: {coll})")


# Check ACLs of a collection and its data objects
def check_acls(ctx, coll, mode):
    group_coll = get_group_coll(ctx, coll)

    if group_coll != "":
        # Check ACLs of provided collection
        group_acls = get_coll_acls(ctx, group_coll)
        coll_acls = get_coll_acls(ctx, coll)
        compare_acls(ctx, coll_acls, group_acls, coll, mode)

        # Check ACLs of provided collection's data objects
        dataobjs = get_dataobjs(ctx, coll)

        if len(dataobjs) > 0:
            for data_obj in dataobjs:
                dataobj_acls = get_data_acls(ctx, coll, data_obj)
                compare_acls(ctx, dataobj_acls, group_acls, f"{coll}/{data_obj}", mode)

        # Check ACLs of provided collection's subcollections
        subcolls = get_subcolls(ctx, coll)

        if len(subcolls) > 0:
            for subcoll in subcolls:
                subcoll_acls = get_coll_acls(ctx, subcoll)
                compare_acls(ctx, subcoll_acls, group_acls, subcoll, mode)

            # Check ACLs of provided collection's subcollections' data objects
            subcoll_dataobjs = get_dataobjs(ctx, subcoll)

            if len(subcoll_dataobjs) > 0:
                for subcoll_dataobj in subcoll_dataobjs:
                    subcoll_dataobj_acls = get_data_acls(ctx, subcoll, subcoll_dataobj)
                    compare_acls(ctx, subcoll_dataobj_acls, group_acls, f"{subcoll}/{subcoll_dataobj}", mode)
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve group collection.")


# Check inheritance of a collection and its subcollections
def check_inheritance(ctx, coll, mode):
    # Check inheritance of collection
    check_coll_inheritance(ctx, coll, mode)

    # Check inheritance of collection's subcollections
    subcolls = get_subcolls(ctx, coll)

    if len(subcolls) > 0:
        for subcoll in subcolls:
            check_coll_inheritance(ctx, subcoll, mode)


# Check and update metadata for a collection
def check_metadata(ctx, coll, mode, user):
    coll_avus = get_avus(ctx, coll, "org_%")

    if bool(coll_avus):
        vault_status = coll_avus['org_vault_status']
        if vault_status == "PUBLISHED" or vault_status == "DEPUBLISHED":
            for (attr, value) in coll_avus.items():
                # Filter AVUs that refer to a path
                if os.path.isabs(value):
                    current_zone = ctx.uuClientZone("")['arguments'][0]
                    avu_zone = value.split('/')[1]
                    if avu_zone != current_zone:
                        ctx.writeLine("stdout", f"WARN: AVU '{attr}' contains zone that does not match current zone. (Metadata zone: '{avu_zone}', current zone: '{current_zone}')")

                        if (mode == "write"):
                            ctx.writeLine("stdout", f"\tRunning in {mode} mode, fixing...")
                            new_value = value.replace(avu_zone, current_zone)

                            # Update zone name
                            try:
                                ctx.msiModAVUMetadata("-C", str(coll), "set", str(attr), str(new_value), "")
                            except Exception:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting AVU '{attr}'.")

                            # Ensure write operation was successful
                            if ensure_fix(ctx, "avu", coll, attr=attr, value=new_value):
                                ctx.writeLine("stdout", "\tDone.")
                            else:
                                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting AVU '{attr}'.")
                    else:
                        ctx.writeLine("stdout", f"OK: AVU '{attr}' contains zone that matches current zone. (Metadata zone: '{avu_zone}', current zone: '{current_zone}')")
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve collection's metadata.")


# Ensures write operation was successful
def ensure_fix(ctx, op, coll, user_id="", access="", attr="", value=""):
    ensured = False

    if access == "read":
        access = ['read', 'read_object']
    elif access == "write":
        access = ['write', 'write_object']

    if op == "acl-add":
        query = genquery.row_iterator(
            "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
            f"COLL_ACCESS_USER_ID = '{user_id}' AND COLL_ACCESS_NAME in {access} AND COLL_NAME like '{coll}'",
            genquery.AS_LIST,
            ctx)

        if query.total_rows() > 0:
            ensured = True
    elif op == "acl-remove":
        query = genquery.row_iterator(
            "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
            f"COLL_ACCESS_USER_ID = '{user_id}' AND COLL_ACCESS_NAME in {access} AND COLL_NAME like '{coll}'",
            genquery.AS_LIST,
            ctx)

        if not (query.total_rows() > 0):
            ensured = True
    elif op == "inheritance":
        query = genquery.row_iterator(
            "COLL_INHERITANCE",
            f"COLL_NAME like '{coll}'",
            genquery.AS_LIST,
            ctx)

        if query.total_rows() > 0:
            for result in query:
                ensured = result[0] == "0"
    elif op == "avu":
        query = genquery.row_iterator(
            "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            f"META_COLL_ATTR_NAME like '{attr}' AND META_COLL_ATTR_VALUE like '{value}' AND COLL_NAME = '{coll}'",
            genquery.AS_LIST,
            ctx)

        if query.total_rows() > 0:
            ensured = True
    return ensured


# Main function to execute the package check rule
def main(rule_args, ctx, rei):
    coll = global_vars["*coll"].strip('"')
    mode = global_vars["*mode"].strip('"')

    try:
        current_user = ctx.uuClientFullNameWrapper("")['arguments'][0]
        current_user_type = ctx.uuGetUserType(current_user, "")['arguments'][1]
    except Exception:
        ctx.writeLine("stdout", "ERROR: Something went wrong while retrieving user information.")

    if current_user_type == 'rodsadmin':  # Only rodsadmin users can run this script
        if coll_exists(ctx, coll):
            if 'vault-' in coll:  # Script should be run on vault collections only
                ctx.writeLine("stdout", f"Executing package check rule for collection: {coll} (mode: {mode})")
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Check if collection ACLs match group ACLs
                check_acls(ctx, coll, mode)
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Check collection inheritance
                check_inheritance(ctx, coll, mode)
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")

                # Update metadata
                check_metadata(ctx, coll, mode, current_user)
                ctx.writeLine("stdout", "----------------------------------------------------------------------------------------------------")
            else:
                ctx.writeLine("stdout", "ERROR: This rule should be run on vault collections only.")
        else:
            ctx.writeLine("stdout", "ERROR: Collection does not exist, try again.")
    else:
        ctx.writeLine("stdout", "ERROR: This rule can only be run by a rodsadmin user.")

INPUT *coll=, *mode=read
OUTPUT ruleExecOut
