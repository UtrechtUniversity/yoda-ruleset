# \file      iiPolicies.r
# \brief     Policy Enforcement Points (PEP) used for the research area are defined here.
#            All processing or policy checks are defined in separate rules outside this file.
#            The arguments and session variables passed to the PEP's are defined in iRODS itself.
# \author    Paul Frederiks
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# XXX: python refactor: Already doesn't work, need replacement? {{{
# previously called from pep_resource_rename_post
#
## \brief This policy is created for enforcing group ACLs when collections or data objects
##        are moved from outside a research group into it.
##
## \param[in] pluginInstanceName  a copy of $pluginInstanceName
## \param[in] KVPairs             a copy of $KVPairs
##
#uuResourceRenamePostResearch(*pluginInstanceName, *KVPairs) {
#	# example match "/mnt/irods01/vault01/home/research-any/possible/path/to/yoda-metadata.json"
#	#DEBUG writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
#	*zone = *KVPairs.user_rods_zone;
#	*dst = *KVPairs.logical_path;
#	iiLogicalPathFromPhysicalPath(*KVPairs.physical_path, *src, *zone);

#	if (*dst like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
#		*srcPathElems = split(*src, "/");
#		*dstPathElems = split(*dst, "/");

#		if (elem(*srcPathElems, 2) != elem(*dstPathElems, 2)) {
#			uuEnforceGroupAcl(*dst);
#		}
#	}
#}
#}}}
