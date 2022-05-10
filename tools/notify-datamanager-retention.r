notifyDatamanagerRetention() {
        *status = '';
        *statusInfo = '';
        *blabla = 'blabla';
        # rule_process_ending_retention_packages(*blabla, *status, *statusInfo);
        writeLine("stdout", "*status");
        writeLine("stdout", "*statusInfo");
}
input null
output ruleExecOut
