# \file      uuTapeArchive.r
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2021-2024, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Perform dmput command.
#
# \param[in] data Physical path of data object.
# \param[in] dmfs Current DMF state of data object.
#
dmput(*data, *hostAddress, *dmfs) {
    #if (*dmfs not like "DUL" && *dmfs not like "OFL" && *dmfs not like "UNM" && *dmfs not like "MIG") {
        msiExecCmd("dmput", *data, *hostAddress, "", "", *dmRes);
        msiGetStdoutInExecCmdOut(*dmRes, *dmStat);
        writeLine("serverLog", "DEBUG: $userNameClient:$clientAddr - Archive dmput started: *data. Returned Status - *dmStat.");
    #}
}


# \brief Perform dmget command.
#
# \param[in] data Physical path of data object.
# \param[in] dmfs Current DMF state of data object.
#
dmget(*data, *hostAddress, *dmfs) {
    #if (*dmfs not like "DUL" && *dmfs not like "REG" && *dmfs not like "UNM" && *dmfs not like "MIG") {
        msiExecCmd("dmget", *data, *hostAddress, "", "", *dmRes);
        msiGetStdoutInExecCmdOut(*dmRes, *dmStat);
        writeLine("serverLog", "DEBUG: $userNameClient:$clientAddr - Archive dmget started: *data. Returned Status - *dmStat.");
    #}
}


# \brief Perform dmattr command.
#
# \param[in]  data Physical path of data object.
# \param[out] dmfs Current DMF state of data object.
#
dmattr(*data, *hostAddress, *dmfs) {
    msiExecCmd("dmattr", *data, *hostAddress, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes, *dmfs);
    *dmfs = trimr(*dmfs, "\n");

    if (*dmfs like "") {
        *dmfs = "INV";
    }
}
