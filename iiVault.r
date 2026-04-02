# \file      iiVault.r
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2026, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

#\ Generic secure copy functionality
# \param[in] argv         argument string for secure copy like "*publicHost inbox /var/www/landingpages/*publicPath";
# \param[in] origin_path  local path of origin file
# \param[out] err         return the error to calling function
#
iiGenericSecureCopy(*argv, *origin_path, *err) {
        *intErr = errorcode(msiExecCmd("securecopy.sh", *argv, "", *origin_path, 1, *cmdExecOut));
        *err = str(*intErr);
        if (*intErr < 0 ) {
                msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
                msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
                writeString("serverLog", "iiGenericSecureCopy: errorcode *err");
                writeString("serverLog", *stderr);
                writeString("serverLog", *stdout);
        }
}

# \brief When inheritance is missing we need to copy ACL's when introducing new data in vault package.
#
# \param[in] path 		path of object that needs the permissions of parent
# \param[in] recursiveFlag 	either "default" for no recursion or "recursive"
#
iiCopyACLsFromParent(*path, *recursiveFlag) {
        uuChopPath(*path, *parent, *child);

        foreach(*row in SELECT COLL_ACCESS_NAME, COLL_ACCESS_USER_ID WHERE COLL_NAME = *parent) {
                *accessName = *row.COLL_ACCESS_NAME;
                *userId = *row.COLL_ACCESS_USER_ID;
                *userFound = false;

                foreach(*user in SELECT USER_NAME WHERE USER_ID = *userId) {
                        *userName = *user.USER_NAME;
                        *userFound = true;
                }

                if (*userFound) {
                        if (*accessName == "own") {
                                writeString("serverLog", "iiCopyACLsFromParent: granting own to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "own", *userName, *path);
                        } else if (*accessName == "read_object") {
                                writeString("serverLog", "iiCopyACLsFromParent: granting read to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "read", *userName, *path);
                        } else if (*accessName == "modify_object") {
                                writeString("serverLog", "iiCopyACLsFromParent: granting write to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "write", *userName, *path);
                        }
                }
        }
}

# \brief Perform admin operations on the vault
#
iiAdminVaultActions() {
	msiExecCmd("admin-vaultactions.sh", uuClientFullName, "", "", 0, *out);
}

# \brief Prepare to archive a data package in the vault
#
iiAdminVaultArchive(*coll, *action) {
	msiExecCmd("admin-vault-archive.sh", uuClientFullName ++ " " ++ *coll ++ " " ++ *action, "", "", 0, *out);
}

# \brief Perform copy to research from vault
#
iiAdminVaultCopyToResearch(*coll, *target, *receiver, *retryCount) {
	msiExecCmd("admin-copy-to-research.sh", uuClientFullName  ++ " " ++ *coll  ++ " " ++ *target  ++ " " ++ *receiver  ++ " " ++ *retryCount, "", "", 0, *out);
}
