# \file
# \brief job
# \author Ton Smeele, Sietse Snel
# \copyright Copyright (c) 2015-2021, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#  This file can be executed manually or scheduled e.g. once a day.
#  It scans an intake collection for datasets and checks the sets, if no collection
#  is provided, it will scan a predefined list on intake groups (*groupList)
#
#  Prerequisite:  the irods user should have write access on the collection and its objects
#
#


uuYcRunIntakeScan {
        *collectionList = list();
        # intake areas can be added to the group list as needed
        *groupList = list('youth');
        *zone = $rodsZoneClient;

        if ( *intakeRoot == 'dummy' ) {
                foreach (*grp in *groupList) {
                        *root = "/*zone/home/grp-intake-*grp";
                        *collectionList = cons( *root, *collectionList);
                }
        }
        else {
                *collectionList = cons (*intakeRoot, *collectionList);
        }

        foreach (*coll in *collectionList) {
                writeLine("stdout","Running intake scan for *coll ...");
                *status = "0";
                rule_intake_scan_for_datasets(*coll, *status);
                if (*status == "0" ) then *result = "ok" else *result = "ERROR (*status)";
                writeLine("stdout","RunIntakeScan for *intakeRoot result = *result");
        }

}

input *intakeRoot='dummy'
output ruleExecOut
