# \file
# \brief     Migrate group manager 0.9.x to the groupmgr-msi-backend version.
# \author    Chris Smeele
# \copyright Copyright (c) 2016, Utrecht university
# \license   GPLv3

# This moves all collection metadata on /zone/group/* to group metadata for
# groups that start with 'priv-' or 'grp-'.
# The 'administrator' attribute is renamed to 'manager' for interface and code
# consistency.

migrate {
    foreach (*groupRow in
             SELECT USER_GROUP_NAME
             WHERE  USER_TYPE = 'rodsgroup') {

        if (*groupRow."USER_GROUP_NAME" like regex '^(grp-|priv-).*') {
            migrateGroup(*groupRow."USER_GROUP_NAME");
        }
    }
}

newAttrExists(*groupName, *attr, *value) {
    *exists = false;
    foreach (*groupMetaRow in
             SELECT META_USER_ATTR_NAME
             WHERE  USER_GROUP_NAME = '*groupName'
             AND    USER_TYPE       = 'rodsgroup'
             AND    META_USER_ATTR_NAME  = '*attr'
             AND    META_USER_ATTR_VALUE = '*value') {

        *exists = true;
        break;
    }
    *exists;
}

setAttr(*groupName, *attr, *value) {
    # Put this in a separate function because the scoping of the *kv ruins
    # everything when running assockv... in a foreach loop.
    *kv.*attr = *value;
    msiAssociateKeyValuePairsToObj(*kv, *groupName, "-u");
}

migrateGroup(*groupName) {
    writeLine("stdout", "Migrating group *groupName");

    foreach (*groupMetaRow in
             SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
             WHERE  COLL_NAME = '/$rodsZoneClient/group/*groupName') {

        *attr  = *groupMetaRow."META_COLL_ATTR_NAME";
        *value = *groupMetaRow."META_COLL_ATTR_VALUE";

        if (*attr == "administrator") {
            *attr = "manager";
        }

        if (newAttrExists(*groupName, *attr, *value)) {
            writeLine("stdout", "* *attr => '*value' (new attr already exists!)");
        } else {
            writeLine("stdout", "- *attr => '*value'");
            setAttr(*groupName, *attr, *value);
        }
    }
    writeLine("stdout", "---> /$rodsZoneClient/group/*groupName can now be removed\n");
}

input null
output ruleExecOut
