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
	*intakePrefix = *grp ++ "intake-"
}

# \brief uuIiGetVaultPrefix 	Get prefix for vault collection
# 
# \param[out] vaultPrefix 		Prefix of vault collection, including
# 								the group prefix
uuIiGetVaultPrefix(*vaultPrefix) {
	uuIiGetGroupPrefix(*grp);
	*vaultPrefix = *grp ++ "vault-";
}

# \breif uuIiGetMetadataPrefix 	Get prefix for metadata which the portal uses
# \param[out] metadataPrefix 	The prefix used for metadata by the portal
uuIiGetMetadataPrefix(*metadataPrefix) {
	*metadataPrefix = "ilab_intake_metadata_";
}