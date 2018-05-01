# \file        uuMail.r
# \brief       Rules to send e-mails from Yoda.
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

	writeLine("serverLog", "[EMAIL] Send email to *to by *actor with title *title.");

	*status = 0;
	*message = "";
}


# \brief New user invitation email.
#
# \param[in]  newUser new user to be informed
# \param[in]  actor   actor of the email
# \param[out] status  zero on success, non-zero on failure
# \param[out] message a user friendly error message
#
uuNewUserMail(*newUser, *actor, *status, *message) {
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