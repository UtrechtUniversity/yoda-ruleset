#!/usr/bin/irule -F

copyOneCollToVault {
	# Copy research folder to vault.
    *return = "";
    rule_folder_secure(*coll, *return);
}
input *coll=""
output ruleExecOut
