processPublicationTest() {

       writeLine("stdout", "BEFORE PUBLICATION TEST");
       *status = '';
       *statusInfo = '';

       *colName = '/tempZone/home/vault-def1test5/research-def1test5[1597443311]';
       rule_process_republication(*colName, *status, *statusInfo);
       writeLine("stdout", "Status *status");
       writeLine("stdout", "Status info *statusInfo");
       *status = 'Success';

       succeed;


}
input null
output ruleExecOut

