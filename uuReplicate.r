# \file      uuReplicate.r
# \brief     Replication functions.
# \author    Ton Smeele
# \copyright Copyright (c) 2015-2018, Utrecht University. All rights reserved.
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
    msiAssociateKeyValuePairsToObj(*kv, *object, "-d");
    #writeLine("serverLog", "uuReplicateAsynchronously: Replication scheduled for *object");
}
