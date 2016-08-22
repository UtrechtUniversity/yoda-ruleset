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
# \param[out] modified      Unix timestamp of the modify datetime of the file that
#                           was modified last
iiFileCount(*path, *totalSize, *dircount, *filecount, *modified) {
    *dircount = "0";
    *filecount = "0";
    *totalSize = "0";
    *data_modified = "0";
    *coll_modified = "0";
    *meta_coll_modified = "0";

    msiMakeGenQuery("sum(DATA_SIZE), count(DATA_ID), max(DATA_MODIFY_TIME)", "COLL_NAME like '*path%'", *GenQInp);
    msiExecGenQuery(*GenQInp, *GenQOut);
    foreach(*GenQOut) {
        msiGetValByKey(*GenQOut, "DATA_SIZE", *totalSize);
        msiGetValByKey(*GenQOut, "DATA_ID", *filecount);
        msiGetValByKey(*GenQOut, "DATA_MODIFY_TIME", *data_modified);
        break;
    }

    msiMakeGenQuery("count(COLL_ID), max(COLL_MODIFY_TIME), max(META_COLL_MODIFY_TIME)", "COLL_NAME like '*path%'", *GenQInp2);
    msiExecGenQuery(*GenQInp2, *GenQOut2);
    foreach(*GenQOut2) {
        writeLine("serverLog", *GenQOut2);
        msiGetValByKey(*GenQOut2, "COLL_ID", *dircount);
        msiGetValByKey(*GenQOut2, "COLL_MODIFY_TIME", *coll_modified);
        msiGetValByKey(*GenQOut2, "META_COLL_MODIFY_TIME", *meta_coll_modified);
        break;
    }

    *data_modified = int(*data_modified);
    *coll_modified = int(*coll_modified);
    *meta_coll_modified = int(*meta_coll_modified);
    *modified = str(max(*data_modified, *coll_modified, *meta_coll_modified));
}


# \brief iiGetFileAttrs 	Obtain useful file attributes for the general intake,
#							such as item size, comment, and lock status
#
# \param[in] collectionName Name of parent collection of the to be observed item
# \param[in] fileName 		Filename of the to be observed item
# \param[out] size 			Integer giving size of file in bytes
# \param[out] comment 		string giving comments if they exist for this item
iiGetFileAttrs(*collectionName, *fileName, *size, *comment) {
	foreach(*row in SELECT DATA_SIZE, DATA_COMMENTS WHERE COLL_NAME = *collectionName AND DATA_NAME = *fileName) {
		*size = *row.DATA_SIZE;
		*comment = *row.DATA_COMMENTS;
	}
}
