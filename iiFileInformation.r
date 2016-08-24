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

uuIiGetDirInformation(*collection, *l, *o, *searchval, *buffer, *f, *i, *canSnapshot) {
    *buffer = "";
    *i = 0;
    *s = 0; #selected
    *p = 0; #passed
    *f = 0; #found if filter

    *hasMore = 1;

    msiMakeGenQuery(
        "order_asc(COLL_NAME), COLL_CREATE_TIME",
        "COLL_PARENT_NAME = '*collection'",
        *dirQuery
    );

    msiExecGenQuery(*dirQuery, *result);
    msiGetContInxFromGenQueryOut(*result, *resultSetIndex);

    while(*hasMore > 0) {
        if(*resultSetIndex == 0) {*hasMore = 0; }

        foreach(*result) {
            msiGetValByKey(*result, "COLL_NAME", *dir);
            msiGetValByKey(*result, "COLL_CREATE_TIME", *created)

            *name = triml(*dir, "*collection/");

            *add = false;
            if(*searchval == "") {
                if(*i >= *o && *s < *l) {
                    *add = true;
                }
            } else {
                if(*name like '**searchval*') {
                    *f = *f + 1;
                    if(*p >= *o && *s < *l) {
                        *add = true;
                    } else {
                        *p = *p + 1;
                    }
                }
            }

            if(*add) {
                iiFileCount(*dir, *totalSize, *dircount, *filecount, *modified);
                if(*canSnapshot) {
                    uuIiGetLatestSnapshotInfo(*dir, *version, *datasetID, *datasetPath, *time, *userName, *userZone);
                    *snapinf = "*version+=+*userName+=+*time";
                } else {
                    *snapinf = "+=++=+";
                }

                *buffer = "*buffer++++====++++*name+=+*totalSize+=+*dircount+=+*filecount+=+*created+=+*modified+=+*snapinf"; 
                *s = *s + 1;
            }

            *i = *i + 1;
        }
        if(*hasMore > 0) {msiGetMoreRows(*dirQuery, *result, *resultSetIndex); }
    }
}
#
# \param[in] collectionName name of parent collection
# \param[in] l      limit (int)
# \param[in] o      offset (int)
# \param[in] s      searchstring (string)
# \param[out] buffer l files starting at o
# \param[out] f (int) amount of items that are filtered
# \param[out] i     (int)  total size of data
uuIiGetFilesInformation(*collectionName, *l, *o, *searchval, *buffer, *f, *i) {
    *buffer = "";

    *i = 0;
    *s = 0; #selected
    *p = 0; #passed
    *f = 0; #found if filter

    *hasMore = 1;

    msiMakeGenQuery(
        "order_asc(DATA_NAME), DATA_SIZE, DATA_CREATE_TIME, DATA_MODIFY_TIME",
        "COLL_NAME = '*collectionName'",
        *fileQuery
    );

    msiExecGenQuery(*fileQuery, *result);

    msiGetContInxFromGenQueryOut(*result, *resultSetIndex);
    while(*hasMore > 0) {
        if(*resultSetIndex == 0) { *hasMore = 0; }
        foreach(*result) {
            msiGetValByKey(*result, "DATA_NAME", *name);
            msiGetValByKey(*result, "DATA_SIZE", *size);
            msiGetValByKey(*result, "DATA_CREATE_TIME", *created);
            msiGetValByKey(*result, "DATA_MODIFY_TIME", *modified);
            *searchstring = "*name*size*created*modified";

            *add = false;
            if(*searchval == "") {
                if(*i >= *o && *s < *l) {
                    *add = true;
                }
            } else {
                if(*searchstring like "**searchval*") {
                    *f = *f + 1;
                    if(*p >= *o && *s < *l) {
                        *add = true;
                    } else {
                        *p = *p + 1;
                    }
                }
            }

            if(*add) {
                *buffer = "*buffer++++====++++*size+=+*name+=+*created+=+*modified";
                *s = *s + 1;
            }

            *i = *i + 1;
        }
        if(*hasMore > 0) {msiGetMoreRows(*fileQuery, *result, *resultSetIndex); }
    }
}
