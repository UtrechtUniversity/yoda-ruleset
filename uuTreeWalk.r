# \file
# \brief generic function to walk collection trees
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

#test {
#	uuTreeWalk(*direction, *topLevelCollection, *ruleToProcess);
#}


# \brief walks through a collection tree and calls an arbitrary rule for each tree-item
# 
# \param[in] direction           can be "forward" or "reverse" 
#                                forward means process collection itself, then childs
#                                reverse means process childs first
#                                reverse is useful e.g. to delete collection trees
# \param[in] topLevelCollection  pathname of the root of the tree, must be collection
#                                NB: the root itself will not be processed, only children
# \param[in] ruleToProcess       name of the rule that can perform an action on tree items
#                                Requirement: rule must be preloaded in rulebase
#                                The rule should expect the following parameters:
#                                  itemPath  = full iRODS path to the collection/object
#                                  itemName  = last part of the itemPath
#                                  itemIsCollection = true if the item is a collection
#                                  buffer = in/out Key-Value variable
#                                       the buffer is maintained by treewalk and passed
#                                       on to the processing rule. can be used by the rule
#                                       to communicate data to subsequent rule invocations
uuTreeWalk(*direction, *topLevelCollection, *ruleToProcess) {

# create a buffer that can be used by the rule that we will call for each item
# content is arbitrary, just put something in to cast the variable to KV in this scope
	*buffer."path" = *topLevelCollection;
# start walking at the root of the tree...
	uuTreeWalkCollection(
			*direction,
			*topLevelCollection,
			*buffer, 
			*ruleToProcess
	);
}
# \brief       return last segment of a pathname
# \param [in]  pathName 
# \param [out] rightMostSegment
uuTreeGetLastSegment(*path, *segment) {
	*pathPart = trimr(*path, "/");
	*segment = substr(*path, strlen(*pathPart) + 1, strlen(*path));
}

# \brief walk a subtree 
# \param [in] direction   can be "forward" or "reverse"
# \param [in] path
# \param [in/out] buffer  (exclusively to be used by the rule we will can)
# \param [in] rule        name of the rule to be executed in the context of a tree-item 
uuTreeWalkCollection(
			*direction,
			*path,
			*buffer, 
			*ruleToProcess
	) {
	uuTreeGetLastSegment(*path, *collection);
	if (*direction == "forward") {
		# first process this collection itself
		eval("{ *ruleToProcess(\*path,\*collection,true,\*buffer); }");
		# and the dataobjects located directly within the collection
		foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = *path) {
			msiGetValByKey(*row, "DATA_NAME", *dataObject);
			eval("{ *ruleToProcess(\*path,\*dataObject,false,\*buffer); }");
		}
		# then increase depth to walk through the subcollections
		foreach (*row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = *path) {
			msiGetValByKey(*row, "COLL_NAME", *subCollectionPath);
			uuTreeWalkCollection(
					*direction,
					*subCollectionPath,
					*buffer, 
					*ruleToProcess
			);
		}
	}
	if (*direction == "reverse") {
		# first deal with any subcollections within this collection
		foreach (*row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = *path) {
			msiGetValByKey(*row, "COLL_NAME", *subCollectionPath);
			uuTreeWalkCollection(
					*direction, 
					*subCollectionPath, 
					*buffer,
					*ruleToProcess
			);
		}
		# when done then process the dataobjects directly located within this collection
		foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = *path) {
			msiGetValByKey(*row, "DATA_NAME", *dataObject);
			eval("{ *ruleToProcess(\*path,\*dataObject,false,\*buffer); }");
		}
		# and lastly process the collection itself
		eval("{ *ruleToProcess(\*path,\*collection,true,\*buffer); }");
	}
}


#
#input *direction="forward",*topLevelCollection="/tsm/home/rods",*ruleToProcess="myRule"
#output ruleExecOut
