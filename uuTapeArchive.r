# \file      uuTapeArchive.r
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2021-2022, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \constant Metadata key for putting data objects offline.
OFFLINESPACEKEY = "SURF_OffLineSpace"

# \constant Resource connected to tape archive.
ARCHIVERESOURCE = "testArchiveVault"

# \constant Host of resource connected to tape archive.
ARCHIVERESOURCEHOST = "tape-archive.yoda.test"


# PEP to intercept the creation of a new object in the vault.
uuTapeArchiveReplicateAsynchronously(*path) {
    *offlineSpaceKey = OFFLINESPACEKEY;
    *archiveResource = ARCHIVERESOURCE;
    *zoneName = $rodsZoneClient;
    # Condition to determine if an object is stored in the vault.
    if (*path like "/"++*zoneName++"/home/vault-*") {
        # Not possible to re-use the existing function here because the AVUs are set and not just added,
        # so multiple calls would overwrite the previous AVUs.
        msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
        msiSetKeyValuePairsToObj(*kvp, *path, "-d");
    }
}


# Rule to replicate the data to Data Archive and then trim the original copy.
# It takes as input the minimum size in bytes of a data object to be archived.
moveDataOffLine(*sizeThreshold) {
    *offlineSpaceKey = OFFLINESPACEKEY;
    # Loop over all the data objects with the attribute *offlineSpaceKey.
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
            # replication of the data object.
            writeLine("serverLog", "[moveDataOffLine] Replica *repl_num of object *obj_path (*data_size) will be moved offline");
            *replstatus = errorcode(msiDataObjRepl(*obj_path, "destRescName=*archiveResource++++replNum=*repl_num++++verifyChksum=", *replOut));
            if (*replstatus == 0) {
                # Removing the metadata.
                msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kvp, *obj_path, "-d"));
                if (*rmstatus != 0) {
                    writeLine("serverLog", "[moveDataOffLine] Remove Key Value Pairs error: Scheduled replication of <*obj_path>: could not remove schedule flag (*rmstatus)");
                }
                # When the replication is successful, trimming the original copy>
                *trimstatus = errorcode(msiDataObjTrim(*obj_path, "null", *repl_num, "1", "null", *trimOut));
                if (*trimstatus != 0) {
                    writeLine("serverLog", "[moveDataOffLine] trim error: Scheduled trimming of <*obj_path> failed (*trimstatus)");
                }
            }
            else {
                writeLine("serverLog", "[moveDataOffLine] repl error: Scheduled replication of <*obj_path> failed (*replstatus)");
            }
        }
        else {
            writeLine("serverLog", "[moveDataOffLine] repl: Scheduled replication of <*obj_path> does not meet the criteria, repl num: <*repl_num>, size:<*data_size>");
            # Removing the metadata.
            if (*repl_num == '0') {
                msiString2KeyValPair("*offlineSpaceKey=*archiveResource", *kvp);
                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kvp, *obj_path, "-d"));
                if (*rmstatus != 0) {
                    writeLine("serverLog", "[moveDataOffLine] Remove Key Value Pairs error: Scheduled replication of <*obj_path>: could not remove schedule flag (*rmstatus)");
                }
            }
        }
    }
}


# PEP to prevent iRODS from reading data that has not been staged to disk.
pep_resource_open_pre(*INSTANCE_NAME, *CONTEXT, *OUT) {
    # The iRODS resource with a storage path on the HSM filesystem
    *archiveResource=ARCHIVERESOURCE

    # If the data object sits on the HSM resource
    if(*CONTEXT.resc_hier == *archiveResource) {
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
              dmattr(*CONTEXT.physical_path, *dmfs);
              uuTapeArchiveSetState(*CONTEXT.logical_path, *CONTEXT.physical_path, *time);
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


# \brief Perform dmget command.
#
# \param[in] data Physical path of data object.
# \param[in] dmfs Current DMF state of data object.
#
dmget(*data, *dmfs) {
    #if (*dmfs not like "DUL" && *dmfs not like "REG" && *dmfs not like "UNM" && *dmfs not like "MIG") {
        *hostAddress = ARCHIVERESOURCEHOST;
        msiExecCmd("dmget", *data, *hostAddress, "", "", *dmRes);
        msiGetStdoutInExecCmdOut(*dmRes, *dmStat);
        writeLine("serverLog", "DEBUG: $userNameClient:$clientAddr - Archive dmget started: *data. Returned Status - *dmStat.");
    #}
}


# \brief Perform dmattr command.
#
# \param[in]  data Physical path of data object.
# \param[out] dmfs Current DMF state of data object.
#
dmattr(*data, *dmfs) {
    *hostAddress = ARCHIVERESOURCEHOST;
    msiExecCmd("dmattr", *data, *hostAddress, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes, *dmfs);
    *dmfs = trimr(*dmfs, "\n");

    if (*dmfs like "") {
        *dmfs = "INV";
    }
}


# \brief Perform admin operations on the vault.
#
# \param[in] data  Logical path of data object.
# \param[in] time  UNIX timestamp.
# \param[in] state Current DMF state of data object.
#
uuTapeArchiveSetState(*path, *physical_path, *timestamp) {
    *hostAddress = ARCHIVERESOURCEHOST;
    *actor = uuClientFullName;
    *argv = " *actor *path *physical_path *timestamp";
    msiExecCmd("admin-tape-archive-set-state.sh", *argv, *hostAddress, "", 0, *out);
}
