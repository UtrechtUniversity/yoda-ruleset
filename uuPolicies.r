# \file      uuPolicies.r
# \brief     iRODS policies for Yoda (changes to core.re).
# \author    Ton Smeele
# \author    Paul Frederiks
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2018, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Restrict access to OS callouts
#
# \param[in]		cmd  name of executable
#
acPreProcForExecCmd(*cmd, *args, *addr, *hint) {
	# rodsadmin is always permitted
	uuGetUserType(uuClientFullName, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	# permit local commands starting with "admin-", when the first argument is the current user
	msiSubstr(*cmd, "0", "6", *prefix);
	if (*prefix == "admin-" && *addr == "" && *hint == "") {
		*name = uuClientFullName;
		# Name is guaranteed to contain no quoting or escaping characters.
		# See uuUserNameIsValid in uuGroupPolicyChecks.r
		if (*args == *name || *args like "*name *") {
			succeed;
		}
	}

	# permit all local commands starting with "scheduled-"
	msiSubstr(*cmd, "0", "10", *prefix);
	if (*args == "" && *addr == "" && *hint == "" &&
	    *prefix == "scheduled-") {
		succeed;
	}

	# permit access to users in group priv-execcmd-all
	*accessAllowed = false;
	foreach (*rows in SELECT USER_GROUP_NAME WHERE USER_NAME='$userNameClient'
		             AND USER_ZONE='$rodsZoneClient') {
		msiGetValByKey(*rows, "USER_GROUP_NAME", *group);
		if (*group == "priv-execcmd-all") {
			*accessAllowed = true;
		}
	}
	if (*accessAllowed == false) {
		cut;
		msiOprDisallowed;
	}
}

# acCreateUserZoneCollections extended to also set inherit on the home coll
# this is needed for groupcollections to allow users to share objects
acCreateUserZoneCollections {
	uuGetUserType($otherUserName, *type);
	if (*type == "rodsuser") {
		# Do not create home directories for regular users.
		# but do create trash directories as iRODS always uses the personal trash folder evan when in a group directory
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/trash/home", $otherUserName);
	} else if (*type == "rodsgroup" && ($otherUserName like "read-*")) {
		# Do not create home directories for read- groups.
	} else {
		# *Do* create home directories for all other user types and groups (e.g.
		# rodsadmin, research-, datamanager- and intake groups).
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/home", $otherUserName);
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/trash/home", $otherUserName);
		msiSetACL("default", "admin:inherit", $otherUserName, "/"++$rodsZoneProxy++"/home/"++$otherUserName);
		if ($otherUserName like regex "research-.*" && uuCollectionExists("/" ++ $rodsZoneProxy ++ UUREVISIONCOLLECTION)) {
			*revisionColl = "/"++$rodsZoneProxy++UUREVISIONCOLLECTION;
			acCreateCollByAdmin(*revisionColl, $otherUserName);
			msiSetACL("default", "admin:inherit", $otherUserName, "*revisionColl/$otherUserName");
		}
	}
}

# delete collections for zoneless username
acPreProcForDeleteUser {
	acDeleteUserZonelessCollections ::: msiRollback;
	msiCommit;
}

# acDeleteUserZonelessCollections: strip zone from name and delete collections
acDeleteUserZonelessCollections {
	*userName = elem(split($otherUserName, "#"), 0);
	acDeleteCollByAdminIfPresent("/"++$rodsZoneProxy++"/home", *userName);
	acDeleteCollByAdminIfPresent("/"++$rodsZoneProxy++"/trash/home", *userName);
}

# acPostProcForDeleteUser is called after a user is removed.
acPostProcForDeleteUser {
	*userAndZone = split($otherUserName, "#");
	*userName = elem(*userAndZone, 0);
	if (size(*userAndZone) > 1) {
		*userZone = elem(*userAndZone, 1);
	} else {
		*userZone = $otherUserZone;
	}
	if (*userZone == "") {
		*userZone = $rodsZoneProxy;
	}

	# Remove external user
	if (*userZone == $rodsZoneProxy && uuExternalUser(*userName)) {
		uuRemoveExternalUser(*userName, *userZone);
	}

	# Log removal of user.
	*actor = uuClientFullName;
	writeLine("serverLog", "User *userName from zone *userZone is removed by *actor.")
}

# acPreProcForObjRename is fired before a data object is renamed or moved.
# Disallows renaming or moving the data object if it is directly under home.
acPreProcForObjRename(*src, *dst) {
        ON($objPath like regex "/[^/]+/home/" ++ ".[^/]*") {
                uuGetUserType(uuClientFullName, *userType);
                if (*userType != "rodsadmin") {
                        cut;
                        msiOprDisallowed;
                }
        }
}

# \brief pep_resource_modified_post
# \param[in,out] out This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_modified_post(*instanceName, *context, *out) {
        on(uuinlist(*instanceName, UUPRIMARYRESOURCES)) {
                uuReplicateAsynchronously(*context.logical_path, *instanceName, UUREPLICATIONRESOURCE);

                # The rules on metadata are run synchronously and could fail.
		# Log errors, but continue with revisions.
                *err = errormsg(uuResourceModifiedPostResearch(*instanceName, *context), *msg);
                if (*err < 0) {
                        writeLine("serverLog", "*err: *msg");
                }
                uuResourceModifiedPostRevision(*instanceName, *context.user_rods_zone, *context.logical_path, UUMAXREVISIONSIZE, UUBLACKLIST);
        }
        # See issue https://github.com/irods/irods/issues/3500.
	# Workaround to avoid debug messages in irods 4.1.8
        on(true) {nop;}
}

# \brief pep_resource_rename_post
# \param[in,out] out This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_rename_post(*instanceName, *context, *out, *newFileName) {
        on(uuinlist(*instanceName, UUPRIMARYRESOURCES)) {
                uuResourceRenamePostResearch(*instanceName, *context);
        }
        # See issue https://github.com/irods/irods/issues/3500.
	# Workaround to avoid debug messages in irods 4.1.8
        on(true) {nop;}
}

# \brief pep_resource_unregister_post
# \param[in,out] out This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_unregistered_post(*instanceName, *context, *out) {
	on (uuinlist(*instanceName, UUPRIMARYRESOURCES)) {
		uuResourceUnregisteredPostResearch(*instanceName, *context);
	}
        # See issue https://github.com/irods/irods/issues/3500.
	# Workaround to avoid debug messages in irods 4.1.8
        on(true) {nop;}
}

# Log auth requests to server log (reproduce behaviour before https://github.com/irods/irods/commit/70144d8251fdf0528da554d529952823b008211b)
pep_api_auth_request_pre(*instanceName, *comm, *request) {
    *proxy_user_name = *comm.proxy_user_name;
    *user_user_name = *comm.user_user_name;
    *client_addr = *comm.client_addr
    writeLine("serverLog", "Agent process started for puser=*proxy_user_name and cuser=*user_user_name from *client_addr");
}
