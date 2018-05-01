# \file        uuMail.r
# \brief       Rules to send emails from Yoda.
# \author      Lazlo Westerhof
# \copyright   Copyright (c) 2018 Utrecht University. All rights reserved.
# \license     GPLv3, see LICENSE.

# \brief Send an email from Yoda.
#
# \param[in]  to      receiver of the email
# \param[in]  actor   initiator of the email
# \param[in]  title   title of the email
# \param[out] status  zero on success, non-zero on failure
# \param[out] message a user friendly error message
#
uuMail(*to, *actor, *title, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	uuValidMail(*to, *valid);
	if (*valid > 0) {
	         writeLine("serverLog", "[EMAIL] Send email to *to by *actor with title *title.");
	}

	*status = 0;
	*message = "";
}


# \brief Check if email address is valid.
#
# \param[in]  email email address to validate
# \param[out] valid one on true, zero on false
#
uuValidMail(*email, *valid) {
        *valid = 0;

        *splitEmail = split(*email, "@");

	if (size(*splitEmail) > 1) {
	        *valid = 1;
	} else {
	        *valid = 0;
	}
}


# \brief New internal user invitation email.
#
# \param[in]  newUser new user to be informed
# \param[in]  actor   actor of the email
# \param[out] status  zero on success, non-zero on failure
# \param[out] message a user friendly error message
#
uuNewInternalUserMail(*newUser, *actor, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*to = *newUser;
        *title = "*actor invites you to join Yoda.";
        uuMail(*to, *actor, *title, *status, *message);
}


# \brief New external user invitation email.
#
# \param[in]  newUser new user to be informed
# \param[in]  actor   actor of the email
# \param[out] status  zero on success, non-zero on failure
# \param[out] message a user friendly error message
#
uuNewExternalUserMail(*newUser, *actor, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*to = *newUser;
        *title = "*actor invites you to join Yoda.";
        uuMail(*to, *actor, *title, *status, *message);
}


# \brief New package published email.
#
# \param[in]  datamanager datamanager to be informed
# \param[in]  actor       actor of the email
# \param[out] status      zero on success, non-zero on failure
# \param[out] message     a user friendly error message
#
uuNewPackagePublishedMail(*datamanager, *actor, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*to = *datamanager;
        *title = "New package published.";
        uuMail(*to, *actor, *title, *status, *message);
}


# \brief Your package published email.
#
# \param[in]  researcher  researcher to be informed
# \param[in]  actor       actor of the email
# \param[out] status      zero on success, non-zero on failure
# \param[out] message     a user friendly error message
#
uuYourPackagePublishedMail(*researcher, *actor, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*to = *researcher;
        *title = "Your package is published.";
        uuMail(*to, *actor, *title, *status, *message);
}
