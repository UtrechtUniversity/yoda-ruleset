#
# Wrapper of file checksum microservice to handle host delegation
#
wrap_msi_file_checksum(*file, *resc, *sum) {
    *host = "";
    *result = "";
    
   foreach (*row in select RESC_LOC where RESC_NAME = *resc) {
        *host = *row.RESC_LOC;
   }
   if (*host == "") {
        *result = "-1";
        writeLine("serverLog","Could not find resource location for *resc when invoking file checksum microservice. Resource probably does not exist.");
   }
   else {
    remote(*host, "null") {
       *result = errorcode(msi.file_checksum(*file, *resc, *sum));
    }
   }
    *result;
}    

input null
output ruleExecOut
