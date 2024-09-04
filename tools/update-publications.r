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
}

input *updateDatacite="Yes", *updateLandingpage="Yes", *updateMOAI="Yes", *package='*'
output ruleExecOut
