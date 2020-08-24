processPublicationTest() {

       writeLine("stdout", "BEFORE PUBLICATION TEST");
       *status = '';
       *statusInfo = '';

       *colName = '/tempZone/home/vault-def1test6/research-def1test6[1598298290]';
       rule_process_publication(*colName, *status, *statusInfo);
       writeLine("stdout", "Status *status");
       writeLine("stdout", "Status info *statusInfo");
       *status = 'Success';

       succeed;


}
input null
output ruleExecOut

