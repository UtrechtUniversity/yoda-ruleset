# \file
# \brief Rules to create and manage datapackages in i-lab
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \constant DPTXTNAME	Name of text file that marks datapackages  
DPTXTNAME = ".yoda-datapackage.txt"

# \brief iiCreatePackage
# \param[in] path	path of Datapackage
iiCreateDataPackage(*path, *status) {
	# Write a marker file to dir
	# Policy rules on that file should handle rest
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
			msiDataObjCopy(*prototype, *dptxt, "forceFlag=", *Status);
		} else {
			# Don't know yet how to handle other errors
			fail(*err);
		}
	}
}

iiGetDPtxtPrototype (*prototype) {
	*prototype = "/$rodsZoneClient/home/public/prototype" ++ DPTXTNAME;
}

iiCreateDPtxtPrototype (*path) {
	*options = "";
	msiDataObjCreate(*path, *options, *fd);

	*msg = "This file marks this folder as a datapackage.\nRemoving it, will remove the datapackage status.\nMoving this directory with this file will set the datapackage status in the new location.\nThe contents of this file is of no consequence.\n"
	msiStrlen(*msg, *len);	
	msiDataObjWrite(*fd, *msg, *len);
	msiDataObjClose(*fd,*status);
}


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

pep_resource_rename_post(*out) {
	# run only at the top of the resource hierarchy and when a DPTXTNAME file is found inside a research group.
	# Unfortunately the source logical_path is not amongst the available data in $KVPairs. The physical_path does include the old path, but not in a convenient format.
	# When a DPTXTNAME file gets moved into a new directory it will be picked up by pep_resource_modified_post. So we don't need to set the Datapackage flag here.
        # This rule only needs to handle the degradation of the Datapackage to a folder when it's moved or renamed.

	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.physical_path like regex ".\*/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
		writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		# the logical_path in $KVPairs is that of the destination
		uuChopPath($KVPairs.logical_path, *dest_parent, *dest_basename);
		# The physical_path is that of the source, but includes the path of the vault. If the vault path includes a home folder, we are screwed.
		*src_parent = trimr($KVPairs.physical_path, "/");
		*src_parent_lst = split(*src_parent, "/");
		# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
		uuListIndexOf(*src_parent_lst, "home", *idx);
		if (*idx < 0) {
			failmsg(-1,"pep_resource_rename_post: Could not find home in $KVPairs.physical_path. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		}
		# skip to the part of the path starting from ../home/..
		for( *el = 0; *el < *idx; *el = *el + 1){
			*src_parent_lst = tl(*src_parent_lst);
		}
		# Prepend with the zone and rejoin to a src_path
		*src_parent_lst	= cons($KVPairs.client_user_zone, *src_parent_lst);
		uuJoin("/", *src_parent_lst, *src_parent);
		*src_parent = "/" ++ *src_parent;
		writeLine("serverLog", "pep_resource_rename_post: \*src_parent = *src_parent");
		if (*dest_basename != DPTXTNAME && *src_parent == *dest_parent) {
			writeLine("serverLog", "pep_resource_rename_post: .yoda-datapackage.txt was renamed to *dest_basename. *src_parent loses datapackage flag.");
			iiSetCollectionType(*parent, "Folder");
		} else if (*src_parent != *dest_parent) {
			# The DPTXTNAME file was moved to another folder or trashed. Check if src_parent still exists and degrade it.
			if (uuCollectionExists(*src_parent)) {
				iiSetCollectionType(*src_parent, "Folder");
				writeLine("serverLog", "pep_resource_rename_post: " ++ DPTXTNAME ++ " was moved to *dest_parent. *src_parent became an ordinary Folder.");
			} else {
				writeLine("serverLog", "pep_resource_rename_post: " ++ DPTXTNAME ++ " was moved to *dest_parent and *src_parent is gone.");
			}
		}
	}
}

pep_resource_unregistered_post(*out) {
	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) {
			writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
	}
}

pep_resource_modified_post(*out) {
	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) {
			writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		if ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
			writeLine("serverLog", "A datapackage is created.");
			uuChopPath($KVPairs.logical_path, *parent, *basename);	
			iiSetCollectionType(*parent, "Datapackage");
		} else {
			writeLine("serverLog", "pep_resource_modified_post: does not concern a .yoda-datapackage.txt inside user visible space.");
	        }
	}
}

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

acCreateUserZoneCollections {
	writeLine("stdout", "acCreateUserZoneCollections was triggered");
	if ($otherUsername like "grp-*") {
		*grpColl = "/$rodsZoneClient/home/$otherUserName";

		iiSetCollectionType(*grpColl, "Research Team");
	}
}

acPostProcForCollCreate {
	on ($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+\$") {
		writeLine("serverLog", "acPostProcForCollCreate: A Research team is created at $collName");
		
		iiSetCollectionType($collName, "Research Team");
	}
       	on ($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]\*/.\*") {
		writeLine("serverLog", "acPostProcForCollCreate: an ordinary folder is created at $collName");
		iiSetCollectionType($collName, "Folder");
	}
}
