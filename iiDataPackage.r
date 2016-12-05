# \file
# \brief Rules to create and manage datapackages in i-lab
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \constant DPTXTNAME	Name of text file that marks datapackages  
DPTXTNAME = '.yoda-datapackage.txt'

# \brief iiCreatePackage
# \param[in] path	path of Datapackage
iiCreateDataPackage(*path, *status) {
	# Write a marker file to dir
	# Policy rules on that file should handle rest
	if (!uuCollectionExists(*path)) {
		fail(-30100);
	}

	*dptxt = *path ++ '/' ++ DPTXTNAME;
	*options = "";
	msiDataObjCreate(*dptxt, *options, *fd);

	*msg = "This file marks this directory as a datapackage.\nRemoving it, will remove the datapackage status.\nMoving this directory with this file will set the datapackage status in the new location.\nThe contents of this file is of no consequence.\n"
	# Using the length of the string instead of the buffer seems wrong, but iRODS offers no other way besides writing a microservice or hiding a DPTXT prototype somewhere
	msiStrlen(*msg, *len);	
	msiStrToBytesBuf(*msg,*buf)	
	msiDataObjWrite(*fd, *buf, *len);
	msiDataObjClose(*fd,*status);
}

acPostProcForCreate {
	ON($objPath like "/" ++ $rodsZoneClient ++ "/home/grp-*" ++ DPTXTNAME) {
	uuChopPath($objPath, *coll, *obj);	
	iiSetCollectionType(*coll, "Datapackage");
	}
}

acPostProcForDelete {
	ON($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
		uuChopPath($objPath, *coll, *obj);
		iiSetCollectionType(*coll, "Folder");
	}
}

acPostProcForCollCreate {
	ON($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+\$") {
		iiSetCollectionType($collName, "Research Team");
	}
}

acPostProcForCollCreate {
	ON($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]\*/.\*") {
		iiSetCollectionType($collName, "Folder");
}
}
