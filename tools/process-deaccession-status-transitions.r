processDeaccessionActions() {
	rule_process_deaccession_status_transitions(*actor, *coll, *status);
}
input *actor="", *coll="", *status=""
output ruleExecOut
