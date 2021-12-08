# Youth cohort utility functions

# \brief Clears a kv-list's contents.
#
# \param kvList
#
uuKvClear(*kvList) {
        *kvList."." = ".";
        foreach (*key in *kvList) {
                *kvList.*key = ".";
        }
}

uuYcObjectIsLocked(*objPath, *locked) {
        msiGetObjType(*objPath, *objType);
        *locked = false;
        if (*objType == '-d') {
                uuChopPath(*objPath, *collection, *dataName);
                foreach (*row in SELECT META_DATA_ATTR_VALUE
                                        WHERE COLL_NAME = '*collection'
                                          AND DATA_NAME = '*dataName'
                                          AND META_DATA_ATTR_NAME = 'to_vault_lock'
                        ) {
                        *locked = true;
                        break;
                }
        } else {
                foreach (*row in SELECT META_COLL_ATTR_VALUE
                                        WHERE COLL_NAME = '*objPath'
                                          AND META_COLL_ATTR_NAME = 'to_vault_lock'
                        ) {
                        *locked = true;
                        break;
                }
        }
}
