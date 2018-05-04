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
uuMail(*to, *actor, *subject, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		*message = "Not allowed.";
		succeed;
	}

        uuGetMailConfig(*mailConfig);
	if (int(*mailConfig.sendNotifications) != 1) {
	         writeLine("serverLog", "[EMAIL] Notifications are off.");
		 *status = 0;
		 *message = "";
		 succeed;
	}

	uuValidMail(*to, *valid);
	if (*valid > 0) {
	         writeLine("serverLog", "[EMAIL] Send email to *to by *actor with subject *subject.");

		 *body = "Test body";

		 msiCurlMail(*to,
		             *mailConfig.senderEmail,
			     *mailConfig.senderName,
			     *subject, *body,
		             *mailConfig.smtpServer,
		             *mailConfig.smtpUsername,
		             *mailConfig.smtpPassword,
		             *curlCode);

		 if (int(*curlCode) == 0) {
		         writeLine("serverLog", "[EMAIL] Mail sent to *smtpServer.");
		         *status = 0;
		         *message = "";
		 } else {
		         writeLine("serverLog", "[EMAIL] Sending mail failed, CURL error *curlCode.");
		         *status = 1;
		         *message = "Sending mail failed.";
		 }
	} else {
		 *status = 0;
		 *message = "";
	         writeLine("serverLog", "[EMAIL] Ignoring invalid email address: *to.");
	}
}


# \brief Mail configuration is extracted from metadata on the UUSYSTEMCOLLECTION.
#
# \param[out] mailConfig  a key-value-pair containing the configuration
#
uuGetMailConfig(*mailConfig) {
	# Translation from camelCase config key to snake_case metadata attribute
	*configKeys = list(
		 "sendNotifications",
		 "senderEmail",
		 "senderName",
		 "smtpServer",
		 "smtpUsername",
		 "smtpPassword");
	*metadataAttributes = list(
		 "send_notifications",
		 "sender_email",
		 "sender_name",
		 "smtp_server",
		 "smtp_username",
		 "smtp_password");

	*nKeys = size(*configKeys);
	*sysColl = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	*prefix = UUORGMETADATAPREFIX;
	#DEBUG writeLine("serverLog", "uuGetMailConfig: fetching mail configuration from *sysColl");

	# Retrieve all metadata on system collection.
	*kvpList = list();
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *sysColl
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		*kvp.attrName = triml(*row.META_COLL_ATTR_NAME, *prefix);
		*kvp.attrValue = *row.META_COLL_ATTR_VALUE;
		*kvpList = cons(*kvp, *kvpList);
	}

	# Add all metadata keys found to mailConfig with the configKey as key.
	foreach(*kvp in *kvpList) {
		for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
			if (*kvp.attrName == elem(*metadataAttributes, *idx)) {
				*configKey = elem(*configKeys, *idx);
				*mailConfig."*configKey" = *kvp.attrValue;
				break;
			}
		}
	}

	# Check if all config keys are set.
	for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
		*configKey = elem(*configKeys, *idx);
		*err = errorcode(*mailConfig."*configKey");
		if (*err < 0) {
			*metadataAttribute = elem(*metadataAttributes, *idx);
			writeLine("serverLog", "uuGetMailConfig: *configKey missing; please set *metadataAttribute on *sysColl");
			fail;
		}
	}
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
        *subject = "*actor invites you to join Yoda.";
        uuMail(*to, *actor, *subject, *status, *message);
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
        *subject = "*actor invites you to join Yoda.";
        uuMail(*to, *actor, *subject, *status, *message);
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
        *subject = "New package published.";
        uuMail(*to, *actor, *subject, *status, *message);
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
        *subject = "Your package is published.";
        uuMail(*to, *actor, *subject, *status, *message);
}
