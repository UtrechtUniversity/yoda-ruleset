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
	# run at the top of the resource hierarchy and when a DPTXTNAME file is found inside a research group.
	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.physical_path like regex ".\*/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
		writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		uuChopPath($KVPairs.logical_path, *parent, *basename);
		if (*basename != DPTXTNAME) {
			writeLine("serverLog", "pep_resource_rename_post: .yoda-datapackage.txt was renamed to *basename. *parent loses datapackage flag.");
			iiSetCollectionType(*parent, "Folder");
		} else {
			*parent = trimr($KVPairs.logical_path, "/");
			*parent_lst = split(*parent, "/");
			if (elem(*src_path, 2) == "trash") {
				*ori_path_lst = cons(hd(*parent_lst), tl(tl(*parent_lst)));
				uuJoin("/", *ori_path_lst, *ori_path);
				iiSetCollectionType(*ori_path, "Folder");

			} else {
				iiSetCollectionType(*parent, "Datapackage");
				*ori_path = trimr($KVPairs.physical_path, "/");
				*ori_path_lst = split(*ori_path, "/");
				uuListIndexOf(*ori_path_lst, "home", *idx);
				for( *el = 0; *el < *idx; *el = *el + 1){
					*ori_path_lst = tl(*ori_path_lst);
				}
				*ori_path_lst = cons($KVPairs.client_user_zone, *ori_path_lst);
				uuJoin("/", *ori_path_lst, *ori_path); 
				iiSetCollectionType(*ori_path, "Folder");	
			}
		}
	}

}

pep_resource_modified_post(*out) {
	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) {
		if ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
			writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
			writeLine("serverLog", "A datapackage is created.");
			uuChopPath($KVPairs.logical_path, *parent, *basename);	
			iiSetCollectionType(*parent, "Datapackage");
		} else {
			writeLine("serverLog", "pep_resource_modified_post: regex failed");
	        }
	}
}

pep_resource_modified_post(*out) {
	writeLine("serverLog", hd(split($KVPairs.resc_hier, ";")));
	writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
}


acPostProcForOpen {
	writeLine("serverLog", "acPostProcForOpen: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath. acPostProcForOpen called");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
}	

acPostProcForPut {
	writeLine("serverLog", "acPostProcForPut: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath.");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
}

acPostProcForCreate {
	writeLine("serverLog", "acPostProcForPut: \$objPath=$objPath, \$writeFlag=$writeFlag");
#	if ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
#		writeLine("serverLog", "A datapackage is created by $objPath.");
#		uuChopPath($objPath, *coll, *obj);	
#		iiSetCollectionType(*coll, "Datapackage");
#	}
}


acTrashPolicy {
	on ($objPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$") {
		writeLine("serverLog", "A datapackage is losing its marker $objPath. acTrashPolicy called");
	#	uuChopPath($objPath, *coll, *obj);
	#	iiSetCollectionType(*coll, "Folder");
	#	# msiNoTrashCan();
	}
}

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
