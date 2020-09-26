cleanup {
        writeLine("stdout", 'STRT');
        *status = "";
        rule_revisions_clean_up(*bucketcase, str(*endOfCalendarDay), *status);
        writeLine("stdout", 'AFTER');
        writeLine("stdout", *status);
}

input *endOfCalendarDay=0, *bucketcase="B"
output ruleExecOut
