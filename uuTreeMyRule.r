# \file
# \brief Example of a rule to be called by uuTreeWalk
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
# \brief Example of a rule to be called by uuTreeWalk
# 
# \param[in] path  pathname of the tree-item
# \param[in] name  segment of path, name of collection or data object
# \param[in] isCol  true if the object is a collection, otherwise false
# \param[in,out] buffer     
#
uuTreeMyRule(*path, *name, *isCol, *buffer) {
	writeLine("stdout","path        = *path");
	writeLine("stdout","name        = *name");
	writeLine("stdout","isCol       = *isCol");
	writeLine("stdout","buffer[path]= " ++ *buffer."path");
	if (*isCol) {
	   *buffer."path" = *buffer."path"++"=";
	}
}
