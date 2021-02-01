# \file      ycChecksumIndex.r
# \brief     Youth Cohort - generate checksum index of Vault
# \author    Ton Smeele
# \copyright Copyright (c) 2016, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

#test {
#  *root = "/nluu1a/home/grp-vault-youth";
#  *logfile = "/nluu1a/home/grp-intake-youth/checksums.txt";
#  uuYcGenerateDatasetsIndex(*root, *logfile, *status);
#  writeLine("stdout","return status is *status");
#}


# \brief (over)write data object with a list of vault object checksums
#   
# \param[in]  vaultRoot          root collection to be indexed
# \param[in]  destinationObject  dataobject that will be written to
# \param[out] status             0 = success,  nonzero is error
uuYcGenerateDatasetsIndex(*vaultRoot, *destinationObject, *status) {
   *status = 0;
   msiDataObjCreate(*destinationObject, "forceFlag=", *FHANDLE);

   foreach (*row in SELECT COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE 
                    WHERE COLL_NAME = "*vaultRoot" ) {
      *checksum = *row."DATA_CHECKSUM";
      *name     = *row."DATA_NAME";
      *col      = *row."COLL_NAME";
      *size     = *row."DATA_SIZE";
      uuChopChecksum(*checksum, *type, *checksumOut);
      *textLine = "*type *checksumOut *size *col/*name\n";
      msiStrlen(*textLine, *length);
      msiStrToBytesBuf(*textLine, *buffer);
      msiDataObjWrite(*FHANDLE, *buffer, *bytesWritten);
      if (int(*length) != *bytesWritten) then {
         *status = 1;
      }
   }
   foreach (*row in SELECT COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE 
                    WHERE COLL_NAME like '*vaultRoot/%' ) {
      *checksum = *row."DATA_CHECKSUM";
      *name     = *row."DATA_NAME";
      *col      = *row."COLL_NAME";
      *size     = *row."DATA_SIZE";
      uuChopChecksum(*checksum, *type, *checksumOut);
      *textLine = "*type *checksumOut *size *col/*name\n";
      msiStrlen(*textLine, *length);
      msiStrToBytesBuf(*textLine, *buffer);
      msiDataObjWrite(*FHANDLE, *buffer, *bytesWritten);
      if (int(*length) != *bytesWritten) then {
         *status = 1;
      }
   }
   msiDataObjClose(*FHANDLE, *status2);
   *status;
}

#input null
#output ruleExecOut
