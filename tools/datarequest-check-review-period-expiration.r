check {
        writeLine("stdout", 'START checking for expired data request review periods');
        *status = "";
        rule_datarequest_review_period_expiration_check(*status);
#        writeLine("stdout", *status);
}

output ruleExecOut
