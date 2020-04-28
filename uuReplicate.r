# \file      uuReplicate.r
# \brief     Replication functions.
# \author    Ton Smeele
# \author    Chris Smeele
# \copyright Copyright (c) 2015-2020, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Schedule replication of a data object.
#
#  to implement asynchronous replication call this rule as part of pep_resource_write_post
#  e.g.  pep_resource_write_post(*out) {
#           *sourceResource = $pluginInstanceName;
#           if (*sourceResource == 'yournamehere') {
#              uuReplicateAsynchronously($KVPairs.logical_path, *sourceResource, 'yourdestinationhere');
#           }
#        }
#
# \param[in] object	       data object to be replicated
# \param[in] sourceResource    resource to be used as source
# \param[in] targetResource    resource to be used as destination
uuReplicateAsynchronously(*object, *sourceResource, *targetResource) {
    # Mark data object for batch replication by setting 'org_replication_scheduled' metadata.
    msiString2KeyValPair("", *kv);
    msiAddKeyVal(*kv, UUORGMETADATAPREFIX ++ "replication_scheduled", "*sourceResource,*targetResource");
    msiSetKeyValuePairsToObj(*kv, *object, "-d");
    #writeLine("serverLog", "uuReplicateAsynchronously: Replication scheduled for *object");
}

# Scheduled replication batch job.
#
# Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
# The metadata value indicates the source and destination resource.
#
# XXX: This function cannot be ported to Python in 4.2.7:
#      msiDataObjRepl causes a deadlock for files larger than
#      transfer_buffer_size_for_parallel_transfer_in_megabytes (4) due to an iRODS PREP bug.
#
uuReplicateBatch() {
    writeLine("serverLog", "Batch replication job started");
    *count   = 0;
    *countOk = 0;

    *attr = UUORGMETADATAPREFIX ++ "replication_scheduled";
    foreach (*row in SELECT COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE
                     WHERE  META_DATA_ATTR_NAME = '*attr') {
        *count = *count + 1;

        # Perform scheduled replication for one data object.

        *path  = *row."COLL_NAME" ++ "/" ++ *row."DATA_NAME";
        *rescs = *row."META_DATA_ATTR_VALUE";
        *xs    = split(*rescs, ",");
        if (size(*xs) == 2) {
            *from = elem(*xs, 0);
            *to   = elem(*xs, 1);
            *opts = "rescName=*from++++destRescName=*to++++irodsAdmin=";
            *status = errorcode(msiDataObjRepl(*path, *opts, *s));
            if (*status == 0) {
                *countOk = *countOk + 1;

                # Remove replication_scheduled flag.

                # Even the sudo msi respects ACLs.
                # Need to set write or own on the object if we don't have it already.
                errorcode(msiSudoObjAclSet("", "own", uuClientFullName, *path, ""));
                *status = errorcode(msiSudoObjMetaRemove(*path, "-d", "",
                                                         *attr,
                                                         "*from,*to", "", ""));
                if (*status != 0) {
                    writeLine("serverLog", "Error: Scheduled replication of <*path>: could not remove schedule flag (*status)");
                }
            } else {
                writeLine("serverLog", "Error: Scheduled replication of <*path> failed (*status)");
            }
        } else {
            writeLine("serverLog", "Error: Scheduled replication of <*path> skipped: bad meta value <*rescs>");
        }
    }

    writeLine("serverLog", "Batch replication job finished. *countOk/*count objects succesfully replicated.");
}
