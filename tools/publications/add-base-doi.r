#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# Adds base DOI for all data packages or one selected data package.
#
# To update one data package:
# $ irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/publications/add-base-doi.r \
#   '*package="/tempZone/home/vault-mygroup/package[123456789]"'
#
# To update all data packages:
# $ irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/publications/add-base-doi.r
#
addBaseDoi() {
	rule_add_base_doi(*package);
}

input *package='*'
output ruleExecOut
