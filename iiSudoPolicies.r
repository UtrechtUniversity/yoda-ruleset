# \file      iiSudoPolicies.r
# \brief     Contains policy overrides on policies triggered by sudo actions.
# \author    Paul Frederiks
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# This policy override enables the datamanager to manage ACL's in the vault
# it's signature is defined in the sudo microservice
# The implementation is redirected to iiDatamanagerPreSudoObjAclSet in iiDatamanagerPolicies.r
acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	ON (*otherName like regex "(datamanager|research|read)-.*") {
		iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
	}
}
