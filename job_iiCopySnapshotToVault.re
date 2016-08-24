# \file
# \brief job to copy collections that are snapshot locked to vault.
#                       adapted from job_movetovault.re
# \author Jan de Mooij
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#  This file should be executed as part of a recurring crontab job
#  as the irods admin user (i.e. irods user type rodsadmin)
#  e.g. run every minute
#
#  if another instance of the job is running then the vault will be
#  locked and silently ignored
#

uuIiRunCreateSnapshots {
        *zone = $rodsZoneClient;
        *username = $userNameClient;
        *user = "*username#*zone";
        uuGetUserAndZone(*user, *userName, *userZone);
        # uuGroupMemberships(*user, *grouplist);
        uuIiGetIntakePrefix(*intk);
        uuIiGetVaultPrefix(*vlt);
        msiGetIcatTime(*time, "human");
        writeLine("stdout", "[*time] Checking for datapackages to process");
        # foreach(*grp in *grouplist) {
        foreach(*row in SELECT USER_GROUP_NAME WHERE USER_TYPE = 'rodsgroup') {
                *grp = *row.USER_GROUP_NAME;
                if(*grp like "*intk\*"){
                        *grp = substr(*grp, strlen(*intk), strlen(*grp))
                        *intakeRoot = "/*zone/home/*intk*grp";
                        *vaultRoot = "/*zone/home/*vlt*grp";

                        uuIi2Vault(*intakeRoot, *vaultRoot, *status);
                        if (*status == 0 ) then *result = "ok" else *result = "ERROR (*status)";
                }
        }
}


input *intakeRoot='dummy'
output ruleExecOut
