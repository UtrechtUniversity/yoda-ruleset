# \file
# \brief Constants for the ii rules. If architecture changes, only
# 			this file needs be adapted
#
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief uuIiGetGroupPrefix 	Get the prefix for a group collection
#
# \param[out] grpPrefix 		Group collection group prefix
uuIiGetGroupPrefix(*grpPrefix) {
	*grpPrefix = "grp-"
}

# \brief uuIigetIntakePrefix 	Get prefix for intake collection
# 
# \param[out] intakePrefix 		Prefix of intake collection, including
# 								the group prefix
uuIiGetIntakePrefix(*intakePrefix) {
	uuIiGetGroupPrefix(*grp);
	*intakePrefix = *grp
}

# \brief uuIiGetVaultPrefix 	Get prefix for vault collection
# 
# \param[out] vaultPrefix 		Prefix of vault collection, including
# 								the group prefix
uuIiGetVaultPrefix(*vaultPrefix) {
	uuIiGetGroupPrefix(*grp);
	*vaultPrefix = "vault-";
}

# \brief uuIiGetMetadataPrefix 	Get prefix for metadata which the portal uses
#								If this constant is updated, also update
# 								the PHP Portal config
# \param[out] metadataPrefix 	The prefix used for metadata by the portal
uuIiGetMetadataPrefix(*metadataPrefix) {
	*metadataPrefix = "ilab_";
}

# \brief uuIiVersionPrefix 		Get the prefix used for versions (on top
# 								of the default metadata prefix)
# \param[out] versionPrefix 	The prefix used for versions in iRods metadata
uuIiVersionKey(*versionKey, *dependsKey) {
	uuIiGetMetadataPrefix(*prfx);
	*versionKey = *prfx ++ "version";
	*dependsKey = *prfx ++ "depends_on";
}

# \constant GENQMAXROWS Maximum number of rows returned by an iRODS GenQuery or msiGetMoreRows call
GENQMAXROWS = 256

# \constant IIRESEARCHGROUPPREFIX
IIGROUPPREFIX = "research-"

# \constant IIXSDCOLLECTION
IIXSDCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsd"

# \constant IIXSLCOLLECTION
IIXSLCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsl"

# \constant IIFORMELEMENTSCOLLECTION
IIFORMELEMENTSCOLLECTION = UUSYSTEMCOLLECTION ++ "/formelements"

# \constant IIXSDDEFAULTNAME	Name of the fallback default xsd for ilab
IIXSDDEFAULTNAME = "default.xsd"

# \constant IIFORMELEMENTSDEFAULTNAME
IIFORMELEMENTSDEFAULTNAME = "default.xml"

# \constant IIMETADATAXMLNAME
IIMETADATAXMLNAME = "yoda-metadata.xml"

# \constant IIXSLDEFAULTNAME
IIXSLDEFAULTNAME = "default.xsl"

# \constant IIVALIDLOCKS
IIVALIDLOCKS = list("protect", "submit", "tovault");

# \brief all STATES
UNPROTECTED = "UNPROTECTED"
PROTECTED = "PROTECTED"
SUBMITTED = "SUBMITTED"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
ARCHIVED = "ARCHIVED"

# \constant IIFOLDERSTATES
IIFOLDERSTATES = list(UNPROTECTED, PROTECTED, SUBMITTED, APPROVED, REJECTED, ARCHIVED);

# \constant IIFOLDERTRANSITIONS
IIFOLDERTRANSITIONS = list((UNPROTECTED, PROTECTED),
			   (UNPROTECTED, SUBMITTED),
			   (PROTECTED, UNPROTECTED),
			   (PROTECTED, SUBMITTED),
			   (SUBMITTED, APPROVED),
			   (SUBMITTED, REJECTED),
			   (REJECTED, UNPROTECTED),
			   (APPROVED, ARCHIVED),
			   (ARCHIVED, UNPROTECTED));
