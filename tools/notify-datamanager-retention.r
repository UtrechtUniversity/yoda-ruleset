notifyDatamanagerRetention() {
        *status = '';
        *statusInfo = '';
        *dummy = 'bla';
        rule_process_ending_retention_packages(*dummy, *status, *statusInfo);
        writeLine("stdout", "*status");
        writeLine("stdout", "*statusInfo");
}
input null
output ruleExecOut
