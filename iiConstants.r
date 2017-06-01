# \file
# \brief Constants for the ii rules. If architecture changes, only
# 			this file needs be adapted
#
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \constant GENQMAXROWS Maximum number of rows returned by an iRODS GenQuery or msiGetMoreRows call
GENQMAXROWS = 256

# \constant IIRESEARCHGROUPPREFIX
IIGROUPPREFIX = "research-"
 
# \constant IIVAULTPREFIX
IIVAULTPREFIX = "vault-"

# \constant IIXSDCOLLECTION
IIXSDCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsd"

# \constant IIXSLCOLLECTION
IIXSLCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsl"

# \constant IIFORMELEMENTSCOLLECTION
IIFORMELEMENTSCOLLECTION = UUSYSTEMCOLLECTION ++ "/formelements"

# \constant IIXSDDEFAULTNAME Name of the fallback default xsd for ilab
IIXSDDEFAULTNAME = "default.xsd"

# \constant IIFORMELEMENTSDEFAULTNAME
IIFORMELEMENTSDEFAULTNAME = "default.xml"

# \constant IIMETADATAXMLNAME
IIMETADATAXMLNAME = "yoda-metadata.xml"

# \constant IIXSLDEFAULTNAME
IIXSLDEFAULTNAME = "default.xsl"

# \constant IILOCKATTRNAME
IILOCKATTRNAME = UUORGMETADATAPREFIX ++ "lock"

# \constant IISTATUSATTRNAME
IISTATUSATTRNAME = UUORGMETADATAPREFIX ++ "status"

# \brief all STATES
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
			   (SUBMITTED, LOCKED),
			   (SUBMITTED, ACCEPTED),
			   (SUBMITTED, REJECTED),
			   (REJECTED, FOLDER),
			   (ACCEPTED, SECURED),
			   (SECURED, FOLDER))
