#!/usr/bin/irule -F
archiveRule {
    writeLine("stdout", "Tape archive replication job started");
    writeLine("serverLog", "Tape archive replication job started");
    moveDataOffLine(*SIZE_THRESHOLD);
    writeLine("serverLog", "Tape archive replication job finished");
    writeLine("stdout", "Tape archive replication job finished");
}
INPUT *SIZE_THRESHOLD='1000000000'
OUTPUT ruleExecOut
