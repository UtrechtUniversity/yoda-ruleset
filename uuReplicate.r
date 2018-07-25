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
        delay("<PLUSET>1s</PLUSET><EF>1m DOUBLE UNTIL SUCCESS OR 10 TIMES</EF>") {
		# Find object to replicate.
                uuChopPath(*object, *parent, *basename);
                *objectId = 0;
	        *found = false;

		foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID, DATA_RESC_HIER
			WHERE DATA_NAME      = *basename
			AND   COLL_NAME      = *parent
			AND   DATA_RESC_HIER like '*sourceResource%'
		       ) {
			if (!*found) {
			        *found = true;
			        break;
                        }
	        }

		# Skip replication if object does not exists (any more).
	        if (!*found) {
		        writeLine("serverLog", "uuReplicateAsynchronously: DataObject was not found.");
		        succeed;
	        }

		# Replicate object to target resource.
		*options = "rescName=*sourceResource++++destRescName=*targetResource";
                msiDataObjRepl(*object, *options, *status);
        }
}
