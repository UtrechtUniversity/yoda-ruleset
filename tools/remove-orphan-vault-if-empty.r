removeOrphanVaultIfEmpty {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	# Error cases are: Vault does *not* exist, or its base group *still* exists.
	# In other situations the call to this script is valid and should not fail.
	# That is, no error will be thrown if e.g. the vault is not empty.
	# In that case we will simply do nothing.

	uuGroupExists(*vaultName, *vaultExists);

	if (!*vaultExists) {
		failmsg(-1, "Vault group does not exist");
	}

	uuGetBaseGroup(*vaultName, *baseGroup);
	if (*baseGroup != *vaultName) {
		failmsg(-1, "Base group of vault group '*vaultName' still exists: '*baseGroup'");
	}

	# Remove the revision collection first, if it exists.
	#
	# This is done first to prevent entering (temporarily) an illegal group
	# management state:
	# If a vault group were to be deleted while the revisions collection still
	# exists, the group manager policies would not block attempts to reuse the
	# group name, causing errors during groupAdd.

	uuChop(*vaultName, *_, *baseName, "-", true);
	*researchGroup = "research-"++*baseName;

	*revisionColl = "/"++$rodsZoneProxy++UUREVISIONCOLLECTION++"/"++"research-"++*baseName;
	if (uuCollectionExists(*revisionColl)) {
		# The vault belonged to a research group, of which a revision collection still exists.
		# Remove the revision coll as well.

		writeLine("serverLog", "Orphan revision collection '*revisionColl' will be removed");
		# Add ourselves (rods) as an owner.
		msiSudoObjAclSet("recursive", "own", uuClientFullName, *revisionColl, "");
		msiRmColl(*revisionColl, "forceFlag=", *error);
		writeLine("serverLog", "Orphan revision collection '*revisionColl' was removed");
	}

	# Now remove the vault group, if it is empty.

	uuGroupCollIsEmpty(*vaultName, *vaultIsEmpty);

	if (*vaultIsEmpty) {
		msiSudoGroupRemove(*vaultName, "");
		writeLine("serverLog", "Empty orphan vault '*vaultName' was removed");
	} else {
		writeLine("serverLog", "Orphan vault '*vaultName' was not removed as it is non-empty");
	}
}

input *vaultName=""
output ruleExecOut
