# \file      uuLog.r
# \brief     Logging functions.
# \author    Ton Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Start a log and set verbosity level.
#
# \param[in] logDataObjectPath logfile to be used, or "stdout","stderr"
# \param[in] logLevelTreshold  determines what information will be logged
#                              can be "ERROR","WARNING","INFO" or "DEBUG"
#                              DEBUG is most verbose level
# \param[out] logHandle        reference to the log, to be used in subsequent calls
#                              to function uuLog()
#
uuLogOpenAndSetTreshold(*logDataObjectPath, *logLevelTreshold, *logHandle) {
	*logHandle."path" = *logDataObjectPath;
	*logHandle."logLevelTreshold" = *logLevelTreshold;
}

# \brief Truncates the logfile to a near-empty file.
#
# \param[in] logHandle         reference to the log
#
uuLogTruncate(*logHandle) {
	msiGetIcatTime(*timeStamp, "human");
	*logLine = "*timeStamp : INFO :Start of log \n";
	if (
		   *logHandle."path" == "stdout"
		|| *logHandle."path" == "stderr"
		 ) {
		msiDataObjCreate(*logHandle."path", "forceFlag=datasize=0", *fileDescriptor);
		msiDataObjWrite(*fileDescriptor, *logLine, strlen(*logLine));
		msiDataObjClose(*fileDescriptor, *status);
	} else {
		writeString(*logHandle."path", *logLine);
	}
}

# \brief Returns a number corresponding to verbosity of the
#        loglevel, the higher the number, the more verbose.
#
# \param[in]  logLevelName     name of the loglevel
# \param[out] logLevel         relative verbosity, expressed as a number
#
uuLogLevel(*logLevelName, *logLevel) {
	if (*logLevelName == "ERROR") {
		*logLevel = 1;
	} else {
		if (*logLevelName == "WARNING") {
			*logLevel = 2;
		} else {
			if (*logLevelName == "INFO") {
				*logLevel = 3;
			} else {
				if (*logLevelName == "DEBUG") {
					*logLevel = 4;
				} else {
					*logLevel = 4;  # use DEBUG level in case we find an unidentifiable name
				}
			}
		}
	}
}


# \brief Add a message to the logfile.
#
# \param[in] logHandle         reference to the logfile
# \param[in] logLevel          name of the loglevel category that the message belongs to
# \param[in] message           actual text to be logged
#
uuLog(*logHandle,*logLevel,*message) {
	uuLogLevel(*logLevel,*thisLogLevel);
	uuLogLevel(*logHandle."logLevelTreshold",*logTreshold);
	if ( *thisLogLevel <= *logTreshold ) {
		msiGetIcatTime(*timeStamp, "human");
		*logLine = "*timeStamp : *logLevel : *message \n";
		writeString(*logHandle."path", *logLine);
	}
}
