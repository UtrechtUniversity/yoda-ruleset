test {
    for(*i = 0;*i < *groups;*i = *i + 1) {
        msiGetIcatTime(*timestamp, "human");
        *category = *groupName;
        *subcategory = *groupName;
        *description = "This group is created by a test rule at *timestamp";
        *group = "research-*groupName*i";
        *dataClassification = "unspecified";

        writeLine("stdout", "Attempt to create *group");
        uuGroupAdd(*group, *category, *subcategory, *description, *dataClassification, *status, *message);
        writeLine("stdout", "status: *status\n*message");

        writeLine("stdout", "Adding groupmanager to *group");
        uuGroupUserAdd(*group, "groupmanager", *status, *message);
        writeLine("stdout", "*status: *message");

        writeLine("stdout", "Adding researcher to *group");
        uuGroupUserAdd(*group, "researcher", *status, *message);
        writeLine("stdout", "*status: *message");

        writeLine("stdout", "Adding viewer to *group");
        uuGroupUserAdd(*group, "viewer", *status, *message);
        writeLine("stdout", "*status: *message");

        writeLine("stdout", "Changing role of groupmanager to manager");
        uuGroupUserChangeRole(*group, 'groupmanager', 'manager', *status, *message);
        writeLine("stdout", "*status *message");

        writeLine("stdout", "Changing role of viewer to reader");
        uuGroupUserChangeRole(*group, 'viewer', 'reader', *status, *message);
        writeLine("stdout", "*status *message");

        uuGroupGetMembers(*group, true, true, *members);
        writeLine("stdout", "Members in *group:");
        foreach(*member in *members) {
                writeLine("stdout", "  *member");
        }
    }
}

input *groupName="testgroup", *groups=100
output ruleExecOut
