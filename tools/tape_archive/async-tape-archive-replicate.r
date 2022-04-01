#!/usr/bin/irule -F
archiveRule {
  moveDataOffLine(*SIZE_THRESHOLD);
  writeLine("stdout", "Data have been put offline");
}
INPUT *SIZE_THRESHOLD='1000000000'
OUTPUT ruleExecOut
