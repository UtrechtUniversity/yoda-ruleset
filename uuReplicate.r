# \file      uuReplicate.r
# \brief     Replication functions.
# \author    Ton Smeele
# \author    Chris Smeele
# \copyright Copyright (c) 2015-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


#############################################################
# Scheduled replication batch job.
#
# \param[in] verbose           whether to log verbose messages for troubleshooting ('1': yes, not '1': no)
# \param[in] data_id
# \param[in] max_batch_size
# \param[in] delay
uuReplicationBatchRule(*verbose, *data_id, *max_batch_size, *delay) {
    writeLine("serverLog", "[uuReplicationBatchRule] *data_id, *max_batch_size, *delay");

    # Directly pass the parameters to the python batch script
    rule_replication_batch(*verbose, *data_id, *max_batch_size, *delay);
}


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
    # Give rods 'own' access so that they can remove the AVU.
    errorcode(msiSetACL("default", "own", "rods#$rodsZoneClient", *object));

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
#      https://github.com/irods/irods_rule_engine_plugin_python/issues/54
#
# \param[in] verbose           whether to log verbose messages for troubleshooting (1: yes, 0: no)
uuReplicateBatch(*verbose) {
    *stopped = 0;
    foreach (*row in SELECT DATA_ID
                     WHERE  COLL_NAME = "/$rodsZoneClient/yoda/flags" AND DATA_NAME = "stop_replication") {
        *stopped = 1;
    }

    if (*stopped) {
        writeLine("serverLog", "Batch replication job is stopped");
    } else {
        writeLine("serverLog", "Batch replication job started");
        *count   = 0;
        *countOk = 0;
        *printVerbose = bool(*verbose);

        *attr      = UUORGMETADATAPREFIX ++ "replication_scheduled";
        *errorattr = UUORGMETADATAPREFIX ++ "replication_failed";
        foreach (*row in SELECT COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE
                         WHERE  META_DATA_ATTR_NAME = '*attr') {
            *count = *count + 1;

            # Stop scheduled replication if stop flag is set.
            foreach (*row in SELECT DATA_ID
                             WHERE  COLL_NAME = "/$rodsZoneClient/yoda/flags" AND DATA_NAME = "stop_replication") {
                writeLine("serverLog", "Batch replication job is stopped");
                break;
            }

            # Perform scheduled replication for one data object.
            *path  = *row."COLL_NAME" ++ "/" ++ *row."DATA_NAME";
            *rescs = *row."META_DATA_ATTR_VALUE";
            *xs    = split(*rescs, ",");
            if (size(*xs) == 2) {
                *from = elem(*xs, 0);
                *to   = elem(*xs, 1);
                *opts = "rescName=*from++++destRescName=*to++++irodsAdmin=++++verifyChksum=";

                if (*printVerbose) {
                    writeLine("serverLog", "Batch replication: copying *path from *from to *to ...");
                }

                *replstatus = errorcode(msiDataObjRepl(*path, *opts, *s));

                *kv.*attr = "*from,*to";

                # Remove replication_scheduled flag no matter if replication
                # succeeded or not.
                # rods should have been given own access via policy to allow AVU
                # changes.

                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kv, *path, "-d"));
                if (*rmstatus != 0) {
                    # The object's ACLs may have changed.
                    # Force the ACL and try one more time.
                    errorcode(msiSudoObjAclSet("", "own", uuClientFullName, *path, ""));
                    *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kv, *path, "-d"));

                    if (*rmstatus != 0) {
                        writeLine("serverLog", "repl error: Scheduled replication of <*path>: could not remove schedule flag (*rmstatus)");
                    }
                }

                if (*replstatus == 0) {
                    *countOk = *countOk + 1;

                    # Replication OK. Remove any existing error indication attribute.
                    *c = *row."COLL_NAME";
                    *d = *row."DATA_NAME";
                    foreach (*x in SELECT DATA_NAME
                                   WHERE  COLL_NAME            = '*c'
                                     AND  DATA_NAME            = '*d'
                                     AND  META_DATA_ATTR_NAME  = '*errorattr'
                                     AND  META_DATA_ATTR_VALUE = 'true') {

                        # Only try to remove it if we know for sure it exists,
                        # otherwise we get useless errors in the log.
                        *errorkv.*errorattr = "true";
                        errorcode(msiRemoveKeyValuePairsFromObj(*errorkv, *path, "-d"));
                        break;
                    }
                } else {
                    # Set error attribute

                    writeLine("serverLog", "repl error: Scheduled replication of <*path> failed (*replstatus)");
                    *errorkv.*errorattr = "true";
                    errorcode(msiSetKeyValuePairsToObj(*errorkv, *path, "-d"));
                }
            } else {
                writeLine("serverLog", "repl error: Scheduled replication of <*path> skipped: bad meta value <*rescs>");
            }
        }

        writeLine("serverLog", "Batch replication job finished. *countOk/*count objects succesfully replicated.");
    }
}
