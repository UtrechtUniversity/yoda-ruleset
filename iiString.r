# \file
# \brief Additional string functions and utilities
# \author Jan de Mooij
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE


# \brief userIdentifier 	Replaces the at-sign of an email address
#							with the word "at", if the username is
#							an email address
# \param[in] user 	 		Full username, including zone if this should
#								be included in identifier
# \param[out] identifier 	Username where at-sign is replaced with a dot
userIdentifier(*user, *identifier) {
	*mailAndDomain = split(*user, "@");
	if(size(*mailAndDomain) > 1) {
		*identifier = elem(*mailAndDomain, 0) ++ "." ++ elem(*mailAndDomain, 1);
	} else {
		*identifier = *user;
	}
}

# \brief humanDateTime		Gives another format for datetime based
# 							on datetime given by system
# \param[in] unix 			Unix date time [optional if human]
# \param[in] human 			Human date time [optional if unix]
# \param[out] stringtime 	New string time
humanDateTime(*unix, *human, *stringtime) {

}