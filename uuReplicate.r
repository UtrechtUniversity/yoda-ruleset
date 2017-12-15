# \file      uuReplicate.r
# \brief     Replication functions.
# \author    Ton Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
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
#
# NB: this rule uses remote() as workaround for github.com/irods/irods issue:
#     delay() in dynamic pep crashes agent  #3342
#     Fixed in iRODS 4.1.10
#
uuReplicateAsynchronously(*object, *sourceResource, *targetResource) {
   remote("localhost","") {
      delay("<PLUSET>1s</PLUSET><EF>1m DOUBLE UNTIL SUCCESS OR 10 TIMES</EF>") {
         *options = "rescName=*sourceResource++++destRescName=*targetResource";
         msiDataObjRepl(*object, *options, *status);
      }
   }
}
