processDeaccessionActions() {
	rule_process_deaccession_status_transitions(*actor, *coll_b64, *status);
}
input *actor="", *coll_b64="", *status=""
output ruleExecOut
