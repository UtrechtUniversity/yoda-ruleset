cleanup {
        writeLine("stdout", 'START cleaning up revision store');
        *status = "";
        rule_revisions_clean_up(*bucketcase, str(*endOfCalendarDay), *status);
        writeLine("stdout", *status);
}

input *endOfCalendarDay=0, *bucketcase="B"
output ruleExecOut
