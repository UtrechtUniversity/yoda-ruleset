# \file
# \brief     Modify group manager managers metadata to include zone names.
# \author    Chris Smeele
# \copyright Copyright (c) 2017, Utrecht university
# \license   GPLv3

# Note: This update rule depends on the 'migrate-group-metadata.r' migration to
#       have been completed succesfully before this script is run.

# This changes all 'manager' metadata fields on rodsgroups to include a zone
# name. I.e.: "manager => rods" becomes "manager => rods#tempZone".
#
# The zone name is taken from the current user, that is, $rodsZoneClient.
#
# When a manager is encountered whose username does NOT exist in the current
# zone, (i.e. when you have a manager from a different zone), a warning is
# printed and that manager is skipped. Any such cases will need to be migrated
# manually, as this rule will not assume an external zone name for that
# manager.

update {
    foreach (*groupRow in
             SELECT USER_GROUP_NAME
             WHERE  USER_TYPE = 'rodsgroup') {

        updateGroup(*groupRow."USER_GROUP_NAME");
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

updateGroup(*groupName) {
    writeLine("stdout", "Updating managers of group *groupName");

    foreach (*groupMetaRow in
             SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE
             WHERE  USER_GROUP_NAME = '*groupName'
             AND    USER_TYPE       = 'rodsgroup'
             AND    META_USER_ATTR_NAME = 'manager') {

        *manager = *groupMetaRow.'META_USER_ATTR_VALUE';
        if (*manager like '*#*') {
            writeLine("stdout", "* '*manager' (already OK)");
        } else {
            uuGetUserAndZone(*manager, *managerName, *managerZone);
            *new = "*managerName#*managerZone";

            uuUserExists(*new, *userExists);

            if (*userExists) {
                writeLine("stdout", "- '*manager' => '*new'");

                *alreadyExists = newAttrExists(*groupName, "manager", *new);

                *status = 0;
                if (!*alreadyExists) {
                    *status = errorcode(msiSudoObjMetaAdd   (*groupName, "-u", "manager", *new,     "", ""));
                }
                if (*status == 0) {
                    *status = errorcode(msiSudoObjMetaRemove(*groupName, "-u", 0, "manager", *manager, "", ""));
                    if (*status != 0) {
                        writeLine("stdout", "!! MetaRemove FAILED");
                    }
                } else {
                    writeLine("stdout", "!! MetaAdd FAILED");
                }
            } else {
                writeLine("stdout", "!! User '*new' (*manager) does not exist, they're probably in a different zone. This needs manual fixing!");
            }
        }
    }
}

input null
output ruleExecOut
