testArchiveCreation {

    *status = 0;

    msiArchiveCreate(*archiveTargetPath, *sourceCollection, *targetResource, *status);

    if (*status != 0) {
        writeLine("stdout", "Archive creation failed with status: *status");
    } else {
        writeLine("stdout", "Archive created successfully at *archiveTargetPath");
    }
}

INPUT *targetResource="",*sourceCollection="", *archiveTargetPath=""
OUTPUT ruleExecOut
