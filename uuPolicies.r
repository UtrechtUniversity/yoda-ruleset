# \file
# \brief iRODS policies for Yoda (changes to core.re)
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#test {
#	acPreProcForExecCmd("foo");
#}

# \brief ExecCmd policy for group manager commands.
#
# \param[in] cmd
# \param[in] args
# \param[in] addr
# \param[in] hint
#
acPreProcForExecCmd(*cmd, *args, *addr, *hint) {
	ON(*cmd == "group-manager.py") {
		*allowed = false;
		if (
			   *args like regex "add \"[^\\\\'\" ]+\""
			|| *args like regex "set \"[^\\\\'\" ]+\" \"[^\\\\'\" ]+\" \"[^\\\\'\"]+\""
			|| *args like regex "add-user \"[^\\\\'\" ]+\" \"[^'\\\\'\" ]+\""
			|| *args like regex "remove-user \"[^\\\\'\" ]+\" \"[^'\\\\'\" ]+\""
		) {
			*allowed = true;
		}

		if (!*allowed) {
			cut;
			msiOprDisallowed;
			fail;
		}
	}
}


# \brief preProcForExecCmd
# 			limit the use of OS callouts to a user group "priv-execcmd-all"
#
# \param[in]		cmd  name of executable
#
acPreProcForExecCmd(*cmd, *args, *addr, *hint) {
	*accessAllowed = false;
	foreach (*rows in SELECT USER_GROUP_NAME WHERE USER_NAME='$userNameClient'
		             AND USER_ZONE='$rodsZoneClient') {
		msiGetValByKey(*rows, "USER_GROUP_NAME", *group);
		if (*group == "priv-execcmd-all") {
			*accessAllowed = true;
		}
	}
	if (*accessAllowed == false) {
		cut;
		msiOprDisallowed;
	}
}

#input null
#output ruleExecOut
