# \file
# \brief Rules to create and manage datapackages in i-lab
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiCreatePackage	write a marker file to path. Policy rules should handle rest
# \param[in] path	path of Datapackage
# \param[out] status	status of the DPTXTNAME copy action
iiCreateDataPackage(*path, *status) {

	if (!uuCollectionExists(*path)) {
		fail(-30100);
	}

	*dptxt = *path ++ '/' ++ DPTXTNAME;
	iiGetDPtxtPrototype(*prototype);
	*err = errorcode(msiDataObjCopy(*prototype, *dptxt, "forceFlag=", *status));
	if (*err == 0) {
		writeLine("serverLog", "iiCreateDataPackage: status=*status");
	} else {
		writeLine("serverLog", "iiCreateDataPackage: err=*err");

		if (*err == -808000) {
			# The prototype datapackage marker file probably is missing
			iiCreateDPtxtPrototype(*prototype);
			msiDataObjCopy(*prototype, *dptxt, "forceFlag=", *status);
		} else {
			# Don't know yet how to handle other errors
			fail(*err);
		}
	}
}

# \brief iiGetDPtxtPrototype	 Return the location of a DPTXTNAME prototype
# \param[out] prototype	 path of the prototype
iiGetDPtxtPrototype (*prototype) {
	*prototype = "/$rodsZoneClient/home/public/prototype" ++ DPTXTNAME;
}

# \brief iiCreateDPtxtPrototype	Create the prototype file to use by iiCreateDataPackage
iiCreateDPtxtPrototype (*path) {
	*options = "";
	msiDataObjCreate(*path, *options, *fd);

	*msg = "This file marks this folder as a datapackage.\nRemoving it, will remove the datapackage status.\nMoving this directory with this file will set the datapackage status in the new location.\nThe contents of this file is of no consequence.\n"
	msiStrlen(*msg, *len);	
	msiDataObjWrite(*fd, *msg, *len);
	msiDataObjClose(*fd,*status);
}

#  The PEP's below where part of my search to determine which PEP was run in case of creation, modification, removal and moving
#  of the DPTXTNAME file. The static PEP's where not triggered in the case of rule initiated action. Dynamic PEP's where underdocumented.
#  These might be useful in the future.
#
#pep_database_reg_data_obj_post(*out) {
#	writeLine("serverLog", "pep_database_reg_data_obj_post:\n  \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
#}

#pep_resource_create_post(*out) {
#	on (($pluginInstanceName == "irodsResc") && ($KVPairs.logical_path like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
#		writeLine("serverLog", "pep_resource_create_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
#		writeLine("serverLog", "Marking as datapackage");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
	
#}

#pep_resource_open_post(*out) {
#	writeLine("serverLog", "pep_resource_open_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
#}

#pep_resource_modified_post(*out) {
#	writeLine("serverLog", hd(split($KVPairs.resc_hier, ";")));
#	writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
#}


#acPostProcForOpen {
#	writeLine("serverLog", "acPostProcForOpen: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath. acPostProcForOpen called");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
#}	

#acPostProcForPut {
#	writeLine("serverLog", "acPostProcForPut: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath.");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
#}

#acPostProcForCreate {
#	writeLine("serverLog", "acPostProcForPut: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath.");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
#}


#acTrashPolicy {
#	on ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is losing its marker $objPath. acTrashPolicy called");
	#	uuChopPath($objPath, *coll, *obj);
	#	iiSetCollectionType(*coll, "Folder");
	#	# msiNoTrashCan();
#	}
#}

