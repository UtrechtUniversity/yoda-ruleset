#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# Lift embargo on data access when embargo date is passed.
run {
    uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

    if (*usertype != "rodsadmin") {
        failmsg(-1, "This script needs to be run by a rodsadmin");
    }

    writeLine('stdout', 'Start finding vault packages under embargo that can be lifted');
    *result = rule_lift_embargos_on_data_access();
    writeLine('stdout', 'Finished finding vault packages under embargo that can be lifted with status *result');
}
input null
output ruleExecOut
