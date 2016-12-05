testFileCount {
	iiFileCount(*testPath, *totalSize, *dircount, *filecount, *modified);
	writeString("stdout", "totalSize = *totalSize\ndircount = *dircount\n filecount = *filecount\n modified = *modified\n");
}

INPUT *testPath = "/nluu1paul/home/grp-kernel"
OUTPUT ruleExecOut
