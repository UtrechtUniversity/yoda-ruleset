# \file      iiVaultTransitions.r
# \brief     Status transitions for folders in the vault space.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Retrieve current vault folder status
#
# \param[in]  folder	    Path of vault folder
# \param[out] folderStatus  Current status of vault folder
#
iiVaultStatus(*folder, *vaultStatus) {
	*vaultStatusKey = IIVAULTSTATUSATTRNAME;
	*vaultStatus = UNPUBLISHED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *vaultStatusKey) {
		*vaultStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief Retrieve actor of action on vault folder
#
# \param[in]  folder      Path of action vault folder
# \param[out] actionActor Actor of action on vault folder
#
iiVaultGetActionActor(*folder, *actor, *actionActor) {
	# Retrieve vault folder collection id.
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
	        *collId = *row.COLL_ID;
	}

        # Retrieve vault folder action actor.
        *actionActor = "";
        foreach(*row in SELECT ORDER_DESC(META_COLL_MODIFY_TIME), COLL_ID, META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = "org_vault_action_*collId") {
                *err = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actionActor, "get", 2));
                if (*err < 0) {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId contains invalid JSON");
                } else {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId actor is *actionActor");
                }
                break;
        }

        # Fallback actor (rodsadmin).
        if (*actionActor == "") {
                *actionActor = *actor;
        }
}

# \brief Perform admin operations on the vault
#
iiAdminVaultActions() {
	msiExecCmd("admin-vaultactions.sh", uuClientFullName, "", "", 0, *out);
}
