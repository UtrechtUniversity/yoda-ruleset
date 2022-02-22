# \file
# \brief dataset lookup function
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#

#test {
#	uuYcDatasetGetTopLevel("/tsm/home/rods", "x", *collection, *isCol);
#	writeLine("stdout","coll = *collection  and isCol = *isCol");
#}


# \brief uuYcDatasetGetTopLevel  retrieves the collection path and dataset type for a dataset
#
# \param[in]   rootcollection       path of a tree to search for the dataset
# \param[in]	datasetid            unique identifier of the dataset
# \param[out]  topLevelCollection   collection that has the dataset
#                                   if dataset is not found an empty string is returned
# \param[out]  topLevelIsCollection type of dataset: true = collection false = data objects
#
uuYcDatasetGetTopLevel(*rootCollection, *datasetId, *topLevelCollection, *topLevelIsCollection) {
	# datasets can be
	#  A) one collection with a subtree
	#  B) one or more data objects located (possibly with other objects) in same collection
	*topLevelIsCollection = false;
	*topLevelCollection = "";
	# try to find a collection. note we will expect 0 or 1 rows:
	foreach (*row in SELECT COLL_NAME
					WHERE META_COLL_ATTR_NAME = 'dataset_toplevel'
					  AND META_COLL_ATTR_VALUE = '*datasetId'
					  AND COLL_NAME LIKE '*rootCollection/%'
				) {
		*topLevelIsCollection = true;
		msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
	}
	if (! *topLevelIsCollection) {
		# also try the root itself
		foreach (*row in SELECT COLL_NAME
						WHERE META_COLL_ATTR_NAME = 'dataset_toplevel'
						  AND META_COLL_ATTR_VALUE = '*datasetId'
						  AND COLL_NAME = '*rootCollection'
					) {
			*topLevelIsCollection = true;
			msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
		}
	}
	if (! *topLevelIsCollection) {
		# apparently not a collection, let's search for data objects instead
		foreach (*row in SELECT COLL_NAME,DATA_NAME
					WHERE META_DATA_ATTR_NAME = 'dataset_toplevel'
					  AND META_DATA_ATTR_VALUE = '*datasetId'
					  AND COLL_NAME LIKE '*rootCollection/%'
				) {
			msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
			break;
		}
		if (*topLevelCollection == "") {
			# not found yet, maybe data object(s) in the rootcollection itself?

			foreach (*row in SELECT COLL_NAME,DATA_NAME
						WHERE META_DATA_ATTR_NAME = 'dataset_toplevel'
						  AND META_DATA_ATTR_VALUE = '*datasetId'
						  AND COLL_NAME = '*rootCollection'
					) {
				msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
				break;
			}
		} else {
			#  dataset not found!
		}
	}
}

#input null
#output ruleExecOut
