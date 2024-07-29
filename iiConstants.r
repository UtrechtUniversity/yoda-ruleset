# \file
# \brief Constants for the research rules. If architecture changes, only
# 	 this file needs be adapted.
#
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2024, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \constant IIGROUPPREFIX
IIGROUPPREFIX = "research-"

# \constant IIVAULTPREFIX
IIVAULTPREFIX = "vault-"

# \constant IISCHEMACOLLECTION
IISCHEMACOLLECTION = UUSYSTEMCOLLECTION ++ "/schemas"

# \constant IIMETADATAJSONNAME Name of metadata JSON file
IIJSONMETADATA = "yoda-metadata.json"

# \constant IIJSONNAME Name of the metadata JSON
IIJSONNAME = "metadata.json"

# \constant IIJSONUINAME Name of the JSON UI schema
IIJSONUINAME = "uischema.json"

# \constant IIPUBLICATIONCOLLECTION
IIPUBLICATIONCOLLECTION = UUSYSTEMCOLLECTION ++ "/publication"

# \constant IILOCKATTRNAME
IILOCKATTRNAME = UUORGMETADATAPREFIX ++ "lock"

# \constant IISTATUSATTRNAME
IISTATUSATTRNAME = UUORGMETADATAPREFIX ++ "status"

# \constant IICOPYPARAMSNAME
IICOPYPARAMSNAME = UUORGMETADATAPREFIX ++ "copy_to_vault_params"

# \constant IIVAULTSTATUSATTRNAME
IIVAULTSTATUSATTRNAME = UUORGMETADATAPREFIX ++ "vault_status"

# \brief All research folder states.
FOLDER = "";
LOCKED = "LOCKED";
SUBMITTED = "SUBMITTED";
ACCEPTED = "ACCEPTED";
REJECTED = "REJECTED";
SECURED = "SECURED";

# \constant IIFOLDERTRANSITIONS
IIFOLDERTRANSITIONS = list((FOLDER, LOCKED),
			   (FOLDER, SUBMITTED),
			   (LOCKED, FOLDER),
			   (LOCKED, SUBMITTED),
			   (SUBMITTED, FOLDER),
			   (SUBMITTED, ACCEPTED),
			   (SUBMITTED, REJECTED),
			   (REJECTED, LOCKED),
			   (REJECTED, FOLDER),
			   (REJECTED, SUBMITTED),
			   (ACCEPTED, FOLDER),
			   # Backwards compatibility for folders that hold deprecated SECURED status.
			   (SECURED, LOCKED),
			   (SECURED, FOLDER),
			   (SECURED, SUBMITTED))

# \brief All vault package states.
INCOMPLETE = "INCOMPLETE"
UNPUBLISHED = "UNPUBLISHED";
SUBMITTED_FOR_PUBLICATION = "SUBMITTED_FOR_PUBLICATION";
APPROVED_FOR_PUBLICATION = "APPROVED_FOR_PUBLICATION";
PUBLISHED = "PUBLISHED";
PENDING_DEPUBLICATION = "PENDING_DEPUBLICATION";
DEPUBLISHED = "DEPUBLISHED";
PENDING_REPUBLICATION = "PENDING_REPUBLICATION";

# \brief All cronjob states.
CRONJOB_PENDING = "CRONJOB_PENDING"
CRONJOB_PROCESSING = "CRONJOB_PROCESSING"
CRONJOB_RETRY = "CRONJOB_RETRY"
CRONJOB_UNRECOVERABLE = "CRONJOB_UNRECOVERABLE"
CRONJOB_OK = "CRONJOB_OK"
