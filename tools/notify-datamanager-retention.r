notifyDatamanagerRetention() {
        *status = '';
        *statusInfo = '';
        rule_process_ending_retention_packages(*status, *statusInfo);
        writeLine("stdout", "*status");
        writeLine("stdout", "*statusInfo");
}
input null
output ruleExecOut
