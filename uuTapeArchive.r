# \file      uuTapeArchive.r
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2021-2022, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

getParentResource(*resourceId) {
    msiMakeGenQuery("RESC_PARENT, RESC_NAME",
                    "RESC_ID = '*resourceId'", *genQIn);
    msiExecGenQuery(*genQIn, *genQOut);
    foreach(*genQOut){
        msiGetValByKey(*genQOut, "RESC_PARENT", *resc_parent);
        msiGetValByKey(*genQOut, "RESC_NAME", *resc_name);
    }
    *root_resc = *resc_name;
    if (strlen(str(*resc_parent)) > 0) {
        *root_resc = getParentResource(*resc_parent);
    }

    *root_resc;
}


getObjResource(*objPath) {
    msiSplitPath(*objPath, *coll, *objName)
    msiMakeGenQuery("RESC_PARENT, RESC_NAME",
                    "COLL_NAME = '*coll' AND COLL_NAME not like '/%/trash/%' AND DATA_NAME = '*objName'", *genQIn);
    msiExecGenQuery(*genQIn, *genQOut);
    foreach(*genQOut){
        msiGetValByKey(*genQOut, "RESC_PARENT", *resc_parent);
        msiGetValByKey(*genQOut, "RESC_NAME", *resc_name);
    }
    *root_resc = *resc_name;
    if (strlen(str(*resc_parent)) > 0) {
        *root_resc = getParentResource(*resc_parent);
    }

    *root_resc;
}


# PEP to incercept the creation of a new object in the vault
uuTapeArchiveReplicateAsynchronously(*path) {
    *offlineSpaceKey = "SURF_OffLineSpace";
    *archiveResource = "testArchiveVault";
    *zoneName = $rodsZoneClient;
    # Condition to determine if an object is stored in the vault
    if (*path like "/"++*zoneName++"/home/vault-*") {
        # Not possible to re-use the existing function here because the AVUs are set and not just added,
        # so multiple calls would overwrite the previous AVUs
        # uuReplicateAsynchronously(*object, *sourceResource, *targetResource)
        msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
        msiSetKeyValuePairsToObj(*kvp, *path, "-d");
    }
}


# rule to replicate the data to Data Archive and then trim the original copy.
# It takes as input the minimum size in bytes of a data object to be archived.
moveDataOffLine(*sizeThreshold) {

    *offlineSpaceKey = "SURF_OffLineSpace";
    # loop over all the data objects with the attribute SURF_OffLineData
    msiMakeGenQuery("COLL_NAME, DATA_NAME, DATA_REPL_NUM, META_DATA_ATTR_VALUE, DATA_SIZE",
                    "META_DATA_ATTR_NAME = '*offlineSpaceKey' AND COLL_NAME not like '/%/trash/%'", *genQIn);
    msiExecGenQuery(*genQIn, *genQOut);
    foreach(*genQOut){
        msiGetValByKey(*genQOut, "COLL_NAME", *coll_path);
        msiGetValByKey(*genQOut, "DATA_NAME", *obj_name);
        msiGetValByKey(*genQOut, "DATA_REPL_NUM", *repl_num);
        msiGetValByKey(*genQOut, "META_DATA_ATTR_VALUE", *archiveResource);
        msiGetValByKey(*genQOut, "DATA_SIZE", *data_size);

        *obj_path = *coll_path ++ "/" ++ *obj_name;
        if (*repl_num == '0' && double(*data_size) > double(*sizeThreshold)) {
            # replication of the data object
            writeLine("serverLog", "[putDataOffLine] Replica *repl_num of object *obj_path (*data_size) will be moved offline");
            *replstatus = errorcode(msiDataObjRepl(*obj_path, "destRescName=*archiveResource++++replNum=*repl_num++++verifyChksum=", *replOut));
            if (*replstatus == 0) {
                # removing the metadata
                msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kvp, *obj_path, "-d"));
                if (*rmstatus != 0) {
                    writeLine("serverLog", "Remove Key Value Pairs error: Scheduled replication of <*obj_path>: could not remove schedule flag (*rmstatus)");
                }
                # when the replication is successful, trimming the original copy
                *trimstatus = errorcode(msiDataObjTrim(*obj_path, "null", *repl_num, "1", "null", *trimOut));
                if (*trimstatus != 0) {
                    writeLine("serverLog", "trim error: Scheduled trimming of <*obj_path> failed (*trimstatus)");
                }
            }
            else {
                writeLine("serverLog", "repl error: Scheduled replication of <*obj_path> failed (*replstatus)");
            }
        }
        else {
            writeLine("serverLog", "repl: Scheduled replication of <*obj_path> does not meet the criteria, repl num: <*repl_num>, size:<*data_size>");
            # removing the metadata
            if (*repl_num == '0') {
                msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kvp, *obj_path, "-d"));
                if (*rmstatus != 0) {
                    writeLine("serverLog", "Remove Key Value Pairs error: Scheduled replication of <*obj_path>: could not remove schedule flag (*rmstatus)");
                }
            }
        }
    }
}


# PEP to prevent iRODS from reading data that has not been staged to disk.
pep_resource_open_pre(*INSTANCE_NAME, *CONTEXT, *OUT) {
    # The iRODS resource with a storage path on the HSM filesystem
    *RESC="mockTapeArchive"

    # If the data object sits on the HSM resource
    if(*CONTEXT.resc_hier == *RESC) {
        *MDcounter= 0;        # MetaData time flag, used to prevent spam-queries to HSM
        *DIFFTIME= 0;         # base time difference of current system time and last HSM query
        *dmfs="";             # The DMF status used to determine action

        msiGetIcatTime(*time, "unix");
        msiSplitPath(*CONTEXT.logical_path, *iColl, *iData) ;

        ### Pulling existing metadata if it exists
        foreach(*SURF in SELECT META_DATA_ATTR_NAME,
                                META_DATA_ATTR_VALUE
                         WHERE  COLL_NAME = *iColl
                         AND    DATA_NAME = *iData)
        {
            if(*SURF.META_DATA_ATTR_NAME == 'org_tape_archive_time'){
                *MDcounter = 1;
                *DIFFTIME = int(*time) - int(*SURF.META_DATA_ATTR_VALUE);
            }
            if(*SURF.META_DATA_ATTR_NAME == 'org_tape_archive_state'){
                *dmfs = *SURF.META_DATA_ATTR_VALUE;
            }
        }

        # This block is a loop to prevent flooding the system with queries
        # The DIFFTIME variable is how many seconds must pass before re-querying HSM
        # This is because if the data is not on disk, but iRODS tries to access it, DMF is flooded by 1 request every 3 seconds,
        # per each file, until interrupted or data is staged.
        if(*MDcounter == 0) {
              dmattr(*CONTEXT.physical_path, *CONTEXT.logical_path, *time, *dmfs);
        }

        # The block that checks status and permits action if status is good
        if (*dmfs like "REG" || *dmfs like "DUL" || *dmfs like "MIG" || *dmfs like "NEW") {
            # Log access if data is online
            writeLine("serverLog","$userNameClient:"++*CONTEXT.client_addr++" accessed ($connectOption) "++*CONTEXT.logical_path++" (*dmfs) from the Archive.");
        }
        # This block is what to do if data is not staged to disk
        else if (*dmfs like "UNM" || *dmfs like "OFL" || *dmfs like "PAR"){
            # These two lines are for auto-staging
            # By commenting out the dmget call, you can disable auto stage
            # but then you need to manually call the dmget via another
            dmget(*CONTEXT.physical_path, *dmfs);
            failmsg(-1,*CONTEXT.logical_path++" is still on tape, but queued to be staged." );
        } else {
            failmsg(-1,*CONTEXT.logical_path++" is either not on the tape archive, or something broke internal to the system.");
        }
    }
}


dmget(*data, *dmfs) {
    if (*dmfs not like "DUL" && *dmfs not like "REG" && *dmfs not like "UNM" && *dmfs not like "MIG") {
        msiExecCmd("dmget", *data, "", "", "", *dmRes);
        msiGetStdoutInExecCmdOut(*dmRes, *dmStat);
        writeLine("serverLog", "DEBUG: $userNameClient:$clientAddr - Archive dmget started: *data. Returned Status - *dmStat.");
    }
}


dmattr(*data, *irods_path, *time, *dmfs) {
    msiExecCmd("dmattr", *data, "", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes, *dmfs);
    *dmfs = trimr(*dmfs, "\n");

    if (*dmfs like "") {
        *dmfs = "INV";
    }

    # Store DMF state as AVU.
    msiAddKeyVal(*kv1, "org_tape_archive_state", "*dmfs");
    msiSetKeyValuePairsToObj(*kv1, *irods_path, "-d");

    # Store time as AVU.
    msiAddKeyVal(*kv2, "org_tape_archive_time", "*time");
    msiSetKeyValuePairsToObj(*kv2, *irods_path, "-d");
}


# \brief Perform admin operations on the vault
#
uuTapeArchiveSetState(*path, *timestamp, *state) {
    *argv = " *path *timestamp *state";
    msiExecCmd("admin-tape-archive-set-state.sh", *argv, "", "", 0, *out);
}
