# \file
# \brief File statistics functions
#			Functions in this file extract statistics from files
#			and collections
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#

# \brief iiFileCount 		Obtain a count of all files in a collection
#
# \param[in] path 			The full path to a collection (not a file). This
#							is the COLL_NAME.	
# \param[out] totalSize 	Integer giving the sum of the size of all
#							the objects in the collection in bytes
# \param[out] dircount		The number of child directories in this collection
#							this number is determined recursively, so this does
#							include all subdirectories and not only those directly
#							under the given collection
# \param[out] filecount 	The total number of files in this collection. This
#							number is determined recursively, so this does include
#							all subfiles and not just those directly under the 
#							given collection.
# \param[out] locked 		Bool, true if and only if locked for vault or for snapshot.
#							If locked, a user can unlock, but can do nothing else until
#							unlocked.
# \param[out] frozen		Bool, true if and only if frozen for vault or for snapshot.
#							No user action can be taken on this object if this is true
#
iiFileCount(*path, *totalSize, *dircount, *filecount) {
    *dircount = 0;
    *filecount = 0;
    *totalSize = 0;

    foreach(*row in SELECT sum(DATA_SIZE), count(DATA_ID) WHERE COLL_NAME like '*path%') {
        *totalSize = *row.DATA_SIZE;
        *filecount = *row.DATA_ID;
        break;
    }

    foreach(*row in SELECT count(COLL_ID) WHERE COLL_NAME like "*path/%") {
        *dircount = *row.COLL_ID;
        break;
    }
}


# \brief iiGetFileAttrs 	Obtain useful file attributes for the general intake,
#							such as item size, comment, and lock status
#
# \param[in] collectionName Name of parent collection of the to be observed item
# \param[in] fileName 		Filename of the to be observed item
# \param[out] size 			Integer giving size of file in bytes
# \param[out] comment 		string giving comments if they exist for this item
# \param[out] locked 		Bool, true if and only if locked for vault or for snapshot.
#							If locked, a user can unlock, but can do nothing else until
#							unlocked.
# \param[out] frozen		Bool, true if and only if frozen for vault or for snapshot.
#							No user action can be taken on this object if this is true
#
iiGetFileAttrs(*collectionName, *fileName, *size, *comment) {
	foreach(*row in SELECT DATA_SIZE, DATA_COMMENTS WHERE COLL_NAME = *collectionName AND DATA_NAME = *fileName) {
		*size = *row.DATA_SIZE;
		*comment = *row.DATA_COMMENTS;
	}
}
