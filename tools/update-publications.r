#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# Updates publication endpoints (Landing page, MOAI, DataCite) for either all data
# packages or one selected data package.
#
# To update one data package:
# $ irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/update-publications.r \
#   '*package="/tempZone/home/vault-mygroup/package[123456789]"'
#
# To update all data packages:
# $ irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/update-publications.r
#
updatePublications() {
	rule_update_publication(*package, *updateDatacite, *updateLandingpage, *updateMOAI);
	# writeLine("stdout", "[UPDATE PUBLICATIONS] Start for *package");
	# *packagesFound = 0;

	# # Scan for published vault packages.
	# *ContInxOld = 1;
	# msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ2Inp);
	# msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ2Inp);
	# msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_status", *GenQ2Inp);
	# msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", PUBLISHED, *GenQ2Inp);

	# msiExecGenQuery(*GenQ2Inp, *GenQ2Out);
	# msiGetContInxFromGenQueryOut(*GenQ2Out, *ContInxNew);

	# while(*ContInxOld > 0) {
	# 	foreach(*row in *GenQ2Out) {
	# 		*collName = *row.COLL_NAME;

	# 		# Check if this really is a vault package, or selected vault package
	# 		if ((*package == '*' && *collName like regex "/[^/]+/home/vault-.*") ||
	# 		    (*package != '*' && *collName like regex "/[^/]+/home/vault-.*" && *collName == *package ) ) {
	# 		    *packagesFound = 1;
	# 		    *status = ''
	# 		    *statusInfo = '';
	# 		    rule_update_publication(*collName, *updateDatacite, *updateLandingpage, *updateMOAI, *status, *statusInfo);
	# 		    writeLine("stdout", "*collName: *status *statusInfo");
	# 		}
	# 	}

	# 	*ContInxOld = *ContInxNew;
	# 	if(*ContInxOld > 0) {
	# 		msiGetMoreRows(*GenQ2Inp, *GenQ2Out, *ContInxNew);
	# 	}
	# }
	# msiCloseGenQuery(*GenQ2Inp, *GenQ2Out);

	# if (*packagesFound == 0) {
	# 	writeLine("stdout", "[UPDATE PUBLICATIONS] No packages found for *package")
	# }
	# else {
	# 	writeLine("stdout", "[UPDATE PUBLICATIONS] Finished for *package");
	# }
}

input *updateDatacite="Yes", *updateLandingpage="Yes", *updateMOAI="Yes", *package='*'
output ruleExecOut
