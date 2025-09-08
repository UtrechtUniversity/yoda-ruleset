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
    return len(list(genquery.Query(ctx, "COLL_ID", f"COLL_NAME = '{coll}'"))) > 0


# Get group from collection
def get_group_coll(ctx, coll):
    group_coll = ""
    if coll.rsplit('/', 1)[-1].startswith("vault-"):
        group_coll = coll
    else:
        group_query = list(genquery.Query(ctx,
                                          "COLL_PARENT_NAME",
                                          f"COLL_NAME = '{coll}'"))

        if len(group_query) > 0:
            if group_query[0].rsplit('/', 1)[-1].startswith("vault-"):
                group_coll = group_query[0]
            else:   # If parent collection is not group collection, go up another level
                group_coll = get_group_coll(ctx, group_coll)

    return group_coll


def group_exists(ctx, group):
    return len(list(genquery.Query(ctx, "USER_GROUP_NAME", f"USER_GROUP_NAME = '{group}' AND USER_TYPE = 'rodsgroup'"))) > 0

# Get AVUs from a collection
def get_avus(ctx, coll, avu):
    avu_query = list(genquery.Query(ctx,
                                    "ORDER(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE",
                                    f"META_COLL_ATTR_NAME like '{avu}' AND COLL_NAME = '{coll}'"))

    avus = {}
    if len(avu_query) > 0:
        for (attribute, value) in avu_query:
            avus[attribute] = value
    return avus


# Get subcollections of a collection
def get_subcolls(ctx, coll):
    subcoll_query = list(genquery.Query(ctx,
                                        "COLL_NAME",
                                        f"COLL_NAME like '{coll}/%'"))

    if len(subcoll_query) > 0:
        return subcoll_query
    return []


# Get data objects in a collection
def get_dataobjs(ctx, coll):
    data_query = list(genquery.Query(ctx,
                                     "DATA_NAME",
                                     f"COLL_NAME = '{coll}'"))

    if len(data_query) > 0:
        return data_query
    else:
        return []


# Get ACLs of a collection/data object
def get_acls(ctx, coll, data="", item=""):
    acl = []
    if item == "coll" and data == "":
        access_query = list(genquery.Query(ctx,
                                           "ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME",
                                           f"COLL_NAME = '{coll}'"))
    elif item == "dataobj" and data != "":
        access_query = list(genquery.Query(ctx,
                                           "ORDER(DATA_ACCESS_USER_ID), DATA_ACCESS_NAME",
                                           f"COLL_NAME = '{coll}' AND DATA_NAME like '{data}'"))
    else:
        return acl

    if len(access_query) > 0:
        for (user, access) in access_query:
            user_access = {}

            user_access['user_id'] = user
            
            user_access['user_name'] = list(genquery.Query(ctx,
                                                           "USER_NAME",
                                                           f"USER_ID = '{user}'"))[0]

            if access == "read_object":
                user_access['access'] = "read"
            elif access == "modify_object":
                user_access['access'] = "write"
            else:
                user_access['access'] = access

            acl.append(user_access)

    return acl

# Set initial state of group collection (ensure ACLs and inheritance are correct)
def set_group_coll(ctx, coll):
    group_coll_ready = True

    # Get group collection
    group_coll = get_group_coll(ctx, coll)

    ctx.writeLine("stdout", f"Preparing vault group collection before check... (Path: {group_coll})")

    if group_coll != "":
        read_groups = []

        group_name = group_coll.split('/')[-1]
        parts = group_name.split('-')
        base_name = '-'.join(parts[1:])

        read_name = "read-" + base_name
        if group_exists(ctx, read_name):
            read_groups.append(read_name)

        research_name = "research-" + base_name
        if group_exists(ctx, research_name):
            read_groups.append(research_name)

        try:
            category = ctx.uuGroupGetCategory(research_name, '', '')['arguments'][1]
            if category != "":
                datamanager_name = "datamanager-" + str(category)
                if group_exists(ctx, datamanager_name):
                    read_groups.append(research_name)
        except Exception:
            group_coll_ready = False
            ctx.writeLine("stdout", f"ERROR: Something went wrong while getting groups information. (Path: {group_coll})")

        try:
            ctx.msiSetACL("recursive", "admin:noinherit", "", str(group_coll))

            # Ensure write operation was successful
            if not ensure_fix(ctx, "inheritance", group_coll):
                group_coll_ready = False
        except Exception:
            group_coll_ready = False
            ctx.writeLine("stdout", f"ERROR: Something went wrong while setting inheritance. (Path: {group_coll})")

        for group in read_groups:
            try:
                ctx.msiSetACL("default", "admin:read", str(group), str(group_coll))

                # Ensure write operation was successful
                user_id = list(genquery.Query(ctx,
                                                "USER_ID",
                                                f"USER_NAME = '{group}'"))[0]
                if not ensure_fix(ctx, "acl-add", group_coll, user_id=user_id, access="read"):
                    group_coll_ready = False
            except Exception:
                group_coll_ready = False
                ctx.writeLine("stdout", f"ERROR: Something went wrong while setting ACLs. (Path: {group_coll})")
    else:
        group_coll_ready = False
        ctx.writeLine("stdout", "ERROR: Cannot retrieve group collection.")

    return group_coll_ready


# Compare ACLs of a collection/data object with group ACLs
def compare_acls(ctx, acls, g_acls, coll, mode, data=""):
    if data == "":
        path = coll
    else:
        path = f"{coll}/{data}"

    if len(g_acls) > 0 and len(acls) > 0:
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
            
            if user_name in path and acl in acls:  # Vault group should have no permissions on data package
                if not path.endswith(user_name):  # Do not remove if current collection is the group collection itself
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
                            ctx.writeLine("stdout", f"\tERROR: Something went wrong while setting ACLs. (Path: {path})")

                        # Ensure write operation was successful
                        if ensure_fix(ctx, "acl-add", coll, data=data, user_id=user_id, access=access):
                            ctx.writeLine("stdout", "\tDone.")
                        else:
                            ctx.writeLine("stdout", f"\tERROR: ACL was not set correctly. (Path: {path})")

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
                            ctx.msiSetACL("default", "admin:null", str(user_name), str(path))
                        except Exception:
                            ctx.writeLine("stdout", f"\tERROR: Something went wrong while setting ACLs. (Path: {path})")

                        # Ensure write operation was successful
                        if ensure_fix(ctx, "acl-remove", coll, data=data, user_id=user_id, access=access):
                            ctx.writeLine("stdout", "\tDone.")
                        else:
                            ctx.writeLine("stdout", f"\tERROR: ACL was not set correctly. (Path: {path})")
        else:
            ctx.writeLine("stdout", f"OK: ACLs of current collection/data object are correct. (Path: {path})")
    else:
        ctx.writeLine("stdout", f"ERROR: No ACLs found for this collection/data object. (Path: {path})")


# Check ACLs of a collection and its data objects
def check_acls(ctx, coll, mode):
    group_coll = get_group_coll(ctx, coll)

    if group_coll != "":
        # Check ACLs of provided collection
        group_acls = get_acls(ctx, group_coll, item="coll")
        coll_acls = get_acls(ctx, coll, item="coll")
        compare_acls(ctx, coll_acls, group_acls, coll, mode)

        # Check ACLs of provided collection's data objects
        dataobjs = get_dataobjs(ctx, coll)

        if len(dataobjs) > 0:
            for data_obj in dataobjs:
                dataobj_acls = get_acls(ctx, coll, data=data_obj, item="dataobj")
                compare_acls(ctx, dataobj_acls, group_acls, coll, mode, data=data_obj)

        # Check ACLs of provided collection's subcollections
        subcolls = get_subcolls(ctx, coll)

        if len(subcolls) > 0:
            for subcoll in subcolls:
                subcoll_acls = get_acls(ctx, subcoll, item="coll")
                compare_acls(ctx, subcoll_acls, group_acls, subcoll, mode)

                # Check ACLs of provided collection's subcollections' data objects
                subcoll_dataobjs = get_dataobjs(ctx, subcoll)

                if len(subcoll_dataobjs) > 0:
                    for subcoll_dataobj in subcoll_dataobjs:
                        subcoll_dataobj_acls = get_acls(ctx, subcoll, data=subcoll_dataobj, item="dataobj")
                        compare_acls(ctx, subcoll_dataobj_acls, group_acls, subcoll, mode, data=subcoll_dataobj)
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve group collection.")


# Check inheritance of a collection
def check_coll_inheritance(ctx, coll, mode):
    inherit_query = list(genquery.Query(ctx,
                                        "COLL_INHERITANCE",
                                        f"COLL_NAME = '{coll}'"))

    if len(inherit_query) > 0:
        inheritance = "Enabled" if inherit_query[0] == "1" else "Disabled"

    # Vault packages should have inheritance disabled
    if inheritance == "Disabled":
        ctx.writeLine("stdout", f"OK: Inheritance is {inheritance}. (Path: {coll})")
    elif inheritance == "Enabled":
        ctx.writeLine("stdout", f"WARN: inheritance is {inheritance}, should be Disabled. (Path: {coll})")

        if mode == "write":
            ctx.writeLine("stdout", f"\tRunning in {mode} mode, fixing...")

            try:
                ctx.msiSetACL("default", "admin:noinherit", "", str(coll))
            except Exception:
                ctx.writeLine("stdout", f"\tERROR: Something went wrong while setting inheritance. (Path: {coll})")

            # Ensure write operation was successful
            if ensure_fix(ctx, "inheritance", coll):
                ctx.writeLine("stdout", "\tDone.")
            else:
                ctx.writeLine("stdout", f"\tERROR: Inheritance was not set correctly. (Path: {coll})")
    else:
        ctx.writeLine("stdout", f"ERROR: Could not retrieve collection's inheritance. (Path: {coll})")


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
                    current_vault = [sub for sub in coll.split('/') if sub.startswith('vault-')]
                    avu_vault = [sub for sub in value.split('/') if sub.startswith('vault-')]

                    if avu_zone != current_zone:
                        ctx.writeLine("stdout", f"WARN: AVU '{attr}' contains zone that does not match current zone. (Metadata zone: '{avu_zone}', current zone: '{current_zone}')")

                        if (mode == "write"):
                            ctx.writeLine("stdout", f"\tRunning in {mode} mode, fixing...")
                            new_value = value.replace(avu_zone, current_zone)

                            if len(avu_vault) > 0 and avu_vault != "":
                                new_value = new_value.replace(avu_vault[0], current_vault[0])

                            # Update zone name
                            try:
                                ctx.msiModAVUMetadata("-C", str(coll), "set", str(attr), str(new_value), "")
                            except Exception:
                                ctx.writeLine("stdout", f"\tERROR: Something went wrong while setting AVU '{attr}'.")

                            # Ensure write operation was successful
                            if ensure_fix(ctx, "avu", coll, attr=attr, value=new_value):
                                ctx.writeLine("stdout", "\tDone.")
                            else:
                                ctx.writeLine("stdout", f"\tERROR: AVU '{attr}' was not set correctly.")
                    else:
                        ctx.writeLine("stdout", f"OK: AVU '{attr}' contains zone that matches current zone. (Metadata zone: '{avu_zone}', current zone: '{current_zone}')")
    else:
        ctx.writeLine("stdout", "ERROR: Could not retrieve collection's metadata.")


# Ensures write operation was successful
def ensure_fix(ctx, op, coll, data="", user_id="", access="", attr="", value=""):
    ensured = False

    if access == "read":
        access = ['read', 'read_object']
    elif access == "write":
        access = ['write', 'write_object']
    else:
        access = [access]

    if op == "acl-add":
        if data == "":
            if len(list(genquery.Query(ctx,
                                    "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                                    f"COLL_ACCESS_USER_ID = '{user_id}' AND COLL_ACCESS_NAME in {access} AND COLL_NAME = '{coll}'"))) > 0:
                ensured = True
        else:
            if len(list(genquery.Query(ctx,
                                    "DATA_ACCESS_USER_ID, DATA_ACCESS_NAME",
                                    f"DATA_ACCESS_USER_ID = '{user_id}' AND DATA_ACCESS_NAME in {access} AND COLL_NAME = '{coll}' AND DATA_NAME LIKE '{data}'"))) > 0:
                ensured = True            
    elif op == "acl-remove":
        if data == "":
            if len(list(genquery.Query(ctx,
                                    "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                                    f"COLL_ACCESS_USER_ID = '{user_id}' AND COLL_ACCESS_NAME in {access} AND COLL_NAME = '{coll}'"))) == 0:
                ensured = True
        else:
            if len(list(genquery.Query(ctx,
                                    "DATA_ACCESS_USER_ID, DATA_ACCESS_NAME",
                                    f"DATA_ACCESS_USER_ID = '{user_id}' AND DATA_ACCESS_NAME in {access} AND COLL_NAME = '{coll}' AND DATA_NAME LIKE '{data}'"))) == 0:
                ensured = True            
    elif op == "inheritance":
        query = list(genquery.Query(ctx,
                                    "COLL_INHERITANCE",
                                    f"COLL_NAME = '{coll}'"))
        if len(query) > 0:
            ensured = (query[0] == "0")
    elif op == "avu":
        if len(list(genquery.Query(ctx,
                                   "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                   f"META_COLL_ATTR_NAME like '{attr}' AND META_COLL_ATTR_VALUE like '{value}' AND COLL_NAME = '{coll}'"))) > 0:
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

                group_ready = set_group_coll(ctx, coll)

                if group_ready:
                    # Check if collection ACLs match group ACLs
                    check_acls(ctx, coll, mode)

                    # Check collection inheritance
                    check_inheritance(ctx, coll, mode)

                    # Update metadata
                    check_metadata(ctx, coll, mode, current_user)
                else:
                    ctx.writeLine("stdout", "ERROR: Something went wrong while determining initial state of vault group collection.")                
            else:
                ctx.writeLine("stdout", "ERROR: This rule should be run on vault collections only.")
        else:
            ctx.writeLine("stdout", "ERROR: Collection does not exist, try again.")
    else:
        ctx.writeLine("stdout", "ERROR: This rule can only be run by a rodsadmin user.")

INPUT *coll=, *mode=read
OUTPUT ruleExecOut
