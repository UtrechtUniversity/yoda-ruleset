testRule {

        foreach(*row in SELECT COLL_NAME, DATA_PATH WHERE DATA_NAME = 'yoda-metadata.xml' AND COLL_NAME like "/$rodsZoneClient/home/vault-%" AND DATA_RESC_NAME = "irodsResc") {
                *phyPath = *row.DATA_PATH;
                uuChopPath(*row.COLL_NAME, *parent, *dataPackageName)
                *xmlName = *dataPackageName ++ ".xml";
                *argv = "*phyPath *xmlName test metadata 145.100.59.133";
                msiExecCmd("scp_metadata.sh", *argv, "null", "null", "null", *execCmdOut);
                msiGetStdoutInExecCmdOut(*execCmdOut, *stdout);
                msiGetStderrInExecCmdOut(*execCmdOut, *stderr);
                writeLine("stdout", *stdout);
                writeLine("stdout", *stderr);
        }
}
input null
output ruleExecOut
