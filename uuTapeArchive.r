# \file      uuTapeArchive.r
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2021-2025, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Perform daget command.
#
# \param[in] data        Physical path of data object
# \param[in] hostAddress Host where to execute command
#
daget(*data, *hostAddress) {
    *dataArg = execCmdArg(*data);
    msiExecCmd("daget", *dataArg, *hostAddress, "", "", *daRes);
    msiGetStdoutInExecCmdOut(*daRes, *dmStat);
    writeString("serverLog", "DEBUG: $userNameClient:$clientAddr - Archive daget started: *data. Returned Status - *dmStat.");
}


# \brief Perform daattr command.
#
# \param[in]  data        Physical path of data object
# \param[in]  hostAddress Host where to execute command
# \param[out] state       Current DA state of data object
#
daattr(*data, *hostAddress, *state) {
    *dataArg = execCmdArg(*data);
    msiExecCmd("daattr", *dataArg, *hostAddress, "", "", *daRes);
    msiGetStdoutInExecCmdOut(*daRes, *state);
    *state = trimr(*state, "\n");

    if (*state like "") {
        *state = "INV";
    }
}
