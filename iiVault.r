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

# \brief Perform a vault ingest as rodsadmin.
#
iiAdminVaultIngest() {
	msiExecCmd("admin-vaultingest.sh", uuClientFullName, "", "", 0, *out);
}

# TODO
iiVaultGetRetirementActor(*folder, *actor, *actionActor) {
        # TODO: retrieve retirement action actor
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

# \brief Prepare to retire a data package in the vault
#
iiAdminVaultRetire() {
	msiExecCmd("admin-vault-retire.sh", uuClientFullName, "", "", 0, *out);
}

# \brief Perform copy to research from vault
#
iiAdminVaultCopyToResearch(*coll, *target, *receiver, *retryCount) {
	msiExecCmd("admin-copy-to-research.sh", uuClientFullName  ++ " " ++ *coll  ++ " " ++ *target  ++ " " ++ *receiver  ++ " " ++ *retryCount, "", "", 0, *out);
}
