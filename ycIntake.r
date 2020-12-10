# \file
# \brief     Youth Cohort - Intake dataset scanner.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# NOTE: Some caution was taken in the writing of the following KvList functions
#       in response to stability issues we experienced.
#       Those issues later proved to be caused by changes in iRODS 3 introduced
#       after 3.3.1 (see https://github.com/irods/irods-legacy/compare/3.3.1...master ),
#       and not these rules, but we didn't change behaviour here. This
#       explains for example why uuKvExists depends on checked keys being
#       initialized to '.' before checking, and why '.' is used to indicate an
#       empty value.

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

# \brief Clone a key-value list.
#

# The destination list is cleared before copying.
#
# \param[in]  source
# \param[out] dest
#
uuKvClone(*source, *dest) {
	uuKvClear(*dest);
	foreach (*key in *source) {
		*dest.*key = *source.*key;
	}
}

# \brief Merge two key-value lists.
#
# list1 is copied to result, and any key in list2 that was not present in list1
# is added to the result.
#
# \param[in]  list1
# \param[in]  list2
# \param[out] result
#
uuKvMerge(*list1, *list2, *result) {
	uuKvClear(*result);
	uuKvClone(*list1, *result);

	foreach (*key in *list2) {
		*bool = false;
		if (!uuKvExists(*result, *key)) {
			*result.*key = *list2.*key;
		}
	}
}

# \brief Check if a key exists in a key-value list.
#
# \param[in]  kvList
# \param[in]  key
# \param[out] bool
#
uuKvExists(*kvList, *key) =
	(*kvList.*key != '.');


# \brief Sets metadata on an object.
#
# \param[in] path
# \param[in] key
# \param[in] value
# \param[in] type  either "-d" for data objects or "-C" for collections
uuSetMetaData(*path, *key, *value, *type) {
	msiAddKeyVal(*kv, *key, *value);
	#errorcode(msiAddKeyVal(*kv, *key, *value));
	#*kv.*key = *value;
	msiAssociateKeyValuePairsToObj(*kv, *path, *type);
}


# \brief Removes metadata from an object.
#
# \param[in] path
# \param[in] key
# \param[in] value
# \param[in] type  either "-d" for data objects or "-C" for collections
uuRemoveMetaData(*path, *key, *value, *type) {
	msiAddKeyVal(*kv, *key, *value);
	#errorcode(msiAddKeyVal(*kv, *key, *value));
	#*kv.*key = *value;
	msiRemoveKeyValuePairsFromObj(*kv, *path, *type);
}

# \brief Apply dataset metadata to an object in a dataset.
#
# \param[in] scope        a scanner scope containing WEPV values
# \param[in] path         path to the object
# \param[in] isCollection whether the object is a collection
# \param[in] isToplevel   if true, a dataset_toplevel field will be set on the object
#
uuYcIntakeApplyDatasetMetaData(*scope, *path, *isCollection, *isToplevel) {

	*type = if *isCollection then "-C" else "-d";

	*version = if uuKvExists(*scope, "version") then *scope."version" else "Raw";

	uuSetMetaData(*path, "wave",            *scope."wave",            *type);
	uuSetMetaData(*path, "experiment_type", *scope."experiment_type", *type);
	uuSetMetaData(*path, "pseudocode",      *scope."pseudocode",      *type);
	uuSetMetaData(*path, "version",         *version,                 *type);

	*idComponents."wave"            = *scope."wave";
	*idComponents."experiment_type" = *scope."experiment_type";
	*idComponents."pseudocode"      = *scope."pseudocode";
	*idComponents."version"         = *version;
	*idComponents."directory"       = *scope."dataset_directory";

	uuYcDatasetMakeId(*idComponents, *datasetId);

	uuSetMetaData(
		*path,
		"dataset_id",
		*datasetId,
		*type
	);

	if (*isToplevel) {
		uuSetMetaData(*path, "dataset_toplevel", *datasetId, *type);
	}
}

# \brief Apply any available id component metadata to the given object.
#
# To be called only for objects outside datasets. When inside a dataset
# (or at a dataset toplevel), use uuYcIntakeApplyDatasetMetaData() instead.
#
# \param[in] scope        a scanner scope containing some WEPV values
# \param[in] path         path to the object
# \param[in] isCollection whether the object is a collection
#
uuYcIntakeApplyPartialMetaData(*scope, *path, *isCollection) {
	*type = if *isCollection then "-C" else "-d";

	if (uuKvExists(*scope, "wave")) {
		uuSetMetaData(*path, "wave",            *scope."wave",            *type);
	}
	if (uuKvExists(*scope, "experiment_type")) {
		uuSetMetaData(*path, "experiment_type", *scope."experiment_type", *type);
	}
	if (uuKvExists(*scope, "pseudocode")) {
		uuSetMetaData(*path, "pseudocode",      *scope."pseudocode",      *type);
	}
	if (uuKvExists(*scope, "version")) {
		uuSetMetaData(*path, "version",         *scope."version",         *type);
	}
}

# \brief Remove some dataset metadata from an object.
#
# See the function definition for a list of removed metadata fields.
#
# \param[in] path         path to the object
# \param[in] isCollection whether the object is a collection
#
uuYcIntakeRemoveDatasetMetaData(*path, *isCollection) {
	if (*isCollection) {
		*genQOut =
			SELECT COLL_ID, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
			WHERE COLL_NAME = '*path';
	} else {
		uuChopPath(*path, *parent, *baseName);
		*genQOut =
			SELECT DATA_ID, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
			WHERE DATA_NAME = '*baseName' AND COLL_NAME = '*parent';
	}

	foreach (*row in *genQOut) {
		*type      = if *isCollection then "-C" else "-d";
		*attrName  = if *isCollection then *row."META_COLL_ATTR_NAME"  else *row."META_DATA_ATTR_NAME";
		*attrValue = if *isCollection then *row."META_COLL_ATTR_VALUE" else *row."META_DATA_ATTR_VALUE";

		if (
			   *attrName == "wave"
			|| *attrName == "experiment_type"
			|| *attrName == "pseudocode"
			|| *attrName == "version"
			|| *attrName == "dataset_id"
			|| *attrName == "dataset_toplevel"
			|| *attrName == "error"
			|| *attrName == "warning"
			|| *attrName == "dataset_error"
			|| *attrName == "dataset_warning"
	                || *attrName == "unrecognized"
			|| *attrName == "object_count"
			|| *attrName == "object_errors"
			|| *attrName == "object_warnings"
			# Uncomment the following two lines to remove accumulated metadata during testing.
			#|| *attrName == "comment"
			#|| *attrName == "scanned"
		) {
			uuRemoveMetaData(*path, *attrName, *attrValue, *type);
		}
	}
}

# \brief Check whether the tokens gathered so far are sufficient for indentifyng a dataset.
#
# \param[in]  tokens a key-value list of tokens
# \param[out] complete
#
uuYcIntakeTokensIdentifyDataset(*tokens, *complete) {
	*toCheck = list(
		"wave",
		"experiment_type",
		"pseudocode"
		# "version" is optional.
	);

	*complete = true;
	foreach (*check in *toCheck) {
		*bool = false;

		if (!uuKvExists(*tokens, *check)) {
			*complete = false;
			break;
		}
	}
}

# \brief Extract tokens from a string.
#
# \param[in] string
# \param[in] kvList a list of tokens and metadata already detected
#
uuYcIntakeExtractTokens(*string, *kvList) {

	*foundKvs."." = ".";
	# uuStrToLower(*string, *stringLower);
	# uuStrToUpper(*string, *stringUpper);


        # HdR
        *stringLower = *string
        *stringUpper = *string

	if (*stringLower like regex ``^[0-9]{1,2}[wmy]$``) {
		# String contains a wave.
		# Wave validity is checked later on in the dataset checks.
		*foundKvs."wave" = *stringLower;
	} else if (*stringLower like regex ``^[bap][0-9]{5}$``) {
		# String contains a pseudocode.
		*foundKvs."pseudocode" = substr(*stringUpper, 0, strlen(*string));
	} else if (*string like regex ``^[Vv][Ee][Rr][A-Z][a-zA-Z0-9-]*$``) {
		*foundKvs."version" = substr(*string, 3, strlen(*string));
	} else {
# NB: Max no of function parameters is 20 this is a rule engine limitation.  
#     Therefore to instantiate a longer list we need to use the cons function.
		*experimentTypes = list(
			"pci",
			"echo",
			"facehouse",
			"faceemo",
			"coherence",
			"infprogap",
			"infsgaze",
			"infpop",
#			"mriinhibition",
#			"mriemotion",
#			"mockinhibition",
			"chprogap",
			"chantigap",
			"chsgaze",
			"pciconflict",
			"pcivacation",
			"peabody",
			"discount",
			"cyberball",
			"trustgame"
        );
        *experimentTypes = cons("other", *experimentTypes);
# MRI:
        *experimentTypes = cons("inhibmockbehav", *experimentTypes);
        *experimentTypes = cons("inhibmribehav", *experimentTypes);
        *experimentTypes = cons("emotionmribehav", *experimentTypes);
        *experimentTypes = cons("emotionmriscan", *experimentTypes);
        *experimentTypes = cons("anatomymriscan", *experimentTypes);
        *experimentTypes = cons("restingstatemriscan", *experimentTypes);
        *experimentTypes = cons("dtiamriscan", *experimentTypes);
        *experimentTypes = cons("dtipmriscan", *experimentTypes);
        *experimentTypes = cons("mriqcreport", *experimentTypes);
        *experimentTypes = cons("mriqceval", *experimentTypes);
        *experimentTypes = cons("vasmri", *experimentTypes);
        *experimentTypes = cons("vasmock", *experimentTypes);
#
        *experimentTypes = cons("looklisten", *experimentTypes);
        *experimentTypes = cons("handgame", *experimentTypes);
        *experimentTypes = cons("infpeabody", *experimentTypes);
        *experimentTypes = cons("delaygratification", *experimentTypes);
        *experimentTypes = cons("dtimriscan", *experimentTypes);
        *experimentTypes = cons("inhibmriscan", *experimentTypes);
# 16-Apr-2019 fbyoda email request new exp type:
        *experimentTypes = cons("chdualet", *experimentTypes);
#
		uuListContains(*experimentTypes, *stringLower, *etDetected);
		if (*etDetected) {
			*foundKvs."experiment_type" = *stringLower;
		}
	}
	*result."." = ".";
	uuKvMerge(*kvList, *foundKvs, *result);
	*kvList = *result;
}

# \brief Extract one or more tokens from a file / directory name and add dataset
#        information as metadata.
#
# \param[in]     path
# \param[in]     name
# \param[in]     isCollection
# \param[in,out] scopedBuffer
#
uuYcIntakeExtractTokensFromFileName(*path, *name, *isCollection, *scopedBuffer) {
	uuChopFileExtension(*name, *baseName, *extension);
	#writeLine("stdout", "Extract tokens from <*baseName>");

	*parts = split(*baseName, "_");
	foreach (*part in *parts) {
		*subparts = split(*part, "-");
		foreach (*part in *subparts) {
			#writeLine("stdout", "- <*part>");
			uuYcIntakeExtractTokens(*part, *scopedBuffer);
		}
	}
}

# \brief Mark an object as scanned.
#
# Sets the username of the scanner and a timestamp as metadata on the scanned object.
#
# \param[in] path
# \param[in] isCollection
#
uuYcIntakeScanMarkScanned(*path, *isCollection) {
	# TODO: Get time only once, at the start of the scan.
	msiGetIcatTime(*timestamp, "unix");
	uuSetMetaData(
		*path,
		"scanned",
		"$userNameClient:*timestamp",
		if *isCollection then "-C" else "-d"
	);
}

# \brief Check if a file or directory name contains invalid characters.
#
# \param[in] name
#
# \return a boolean
#
uuYcIntakeScanIsFileNameValid(*name)
	= (*name like regex "^[a-zA-Z0-9_.-]+$");

# \brief Recursively scan a directory in a Youth Cohort intake.
#
# \param[in] root      the directory to scan
# \param[in] scope     a scoped kvlist buffer
# \param[in] inDataset whether this collection is within a dataset collection
#
uuYcIntakeScanCollection(*root, *scope, *inDataset) {

	# Scan files under *root.
	foreach (*item in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *root) {

		uuChopFileExtension(*item."DATA_NAME", *baseName, *extension);
		#writeLine("stdout", "");
		#writeLine("stdout", "Scan file " ++ *item."DATA_NAME");

		*path = *item."COLL_NAME" ++ "/" ++ *item."DATA_NAME";

		uuYcObjectIsLocked(*path, false, *locked, *frozen);
		#*frozen = false;
		#*locked = false;

		if (!(*locked || *frozen)) {
			uuYcIntakeRemoveDatasetMetaData(*path, false);
			uuYcIntakeScanMarkScanned(*path, false);

			if (!uuYcIntakeScanIsFileNameValid(*item."DATA_NAME")) {
				msiAddKeyVal(*kv, "error", "File name contains disallowed characters");
				msiAssociateKeyValuePairsToObj(*kv, *path, "-d");
			}

			if (*inDataset) {
				uuYcIntakeApplyDatasetMetaData(*scope, *path, false, false);
			} else {
				*subScope."." = ".";
				uuKvClone(*scope, *subScope);
				uuYcIntakeExtractTokensFromFileName(*item."COLL_NAME", *item."DATA_NAME", false, *subScope);

				uuYcIntakeTokensIdentifyDataset(*subScope, *bool);
				if (*bool) {
					# We found a top-level dataset data object.
					*subScope."dataset_directory" = *item."COLL_NAME";
					uuYcIntakeApplyDatasetMetaData(*subScope, *path, false, true);
					writeLine("stdout",
						"Found dataset toplevel data-object: "
						++   "W<" ++ *subScope."wave"
						++ "> E<" ++ *subScope."experiment_type"
						++ "> P<" ++ *subScope."pseudocode"
						++ "> V<" ++ *subScope."version"
						++ "> D<" ++ *subScope."dataset_directory"
						++ ">"
					);
				} else {
					uuYcIntakeApplyPartialMetaData(*subScope, *path, false);
					msiAddKeyVal(*kv1, "unrecognized", "Experiment type, wave or pseudocode missing from path");
					msiAssociateKeyValuePairsToObj(*kv1, *path, "-d");
				}
			}
		}
	}

	# Scan collections under *root.
	foreach (*item in SELECT COLL_NAME WHERE COLL_PARENT_NAME = *root) {
		uuChopPath(*item."COLL_NAME", *parent, *dirName);
		if (*dirName != "/") {
			#writeLine("stdout", "");
			#writeLine("stdout", "Scan dir " ++ *dirName);

			*path = *item."COLL_NAME";

			uuYcObjectIsLocked(*path, true, *locked, *frozen);
			#*frozen = false;
			#*locked = false;

			if (!(*locked || *frozen)) {
				uuYcIntakeRemoveDatasetMetaData(*path, true);

				if (!uuYcIntakeScanIsFileNameValid(*dirName)) {
					msiAddKeyVal(*kv, "error", "Directory name contains disallowed characters");
					msiAssociateKeyValuePairsToObj(*kv, *path, "-C");
				}

				*subScope."." = ".";
				uuKvClone(*scope, *subScope);

				*childInDataset = *inDataset;
				if (*inDataset) {
					uuYcIntakeApplyDatasetMetaData(*subScope, *path, true, false);
					uuYcIntakeScanMarkScanned(*path, true);
				} else {
					uuYcIntakeExtractTokensFromFileName(*item."COLL_NAME", *dirName, true, *subScope);

					uuYcIntakeTokensIdentifyDataset(*subScope, *bool);
					if (*bool) {
						*childInDataset = true;
						# We found a top-level dataset collection.
						*subScope."dataset_directory" = *path;
						uuYcIntakeApplyDatasetMetaData(*subScope, *path, true, true);
						writeLine("stdout",
							"Found dataset toplevel collection: "
							++   "W<" ++ *subScope."wave"
							++ "> E<" ++ *subScope."experiment_type"
							++ "> P<" ++ *subScope."pseudocode"
							++ "> V<" ++ *subScope."version"
							++ "> D<" ++ *subScope."dataset_directory"
							++ ">"
						);
					} else {
						uuYcIntakeApplyPartialMetaData(*subScope, *path, true);
					}
				}

				uuYcIntakeScanCollection(*item."COLL_NAME", *subScope, *childInDataset);
			}
		}
	}
}

# \brief Run checks on the dataset specified by the given dataset id.
#
# This function adds warnings and errors to objects within the dataset.
#
# \param[in] root
# \param[in] id
#
uuYcIntakeCheckDataset(*root, *id) {
	uuYcDatasetGetToplevelObjects(*root, *id, *toplevels, *isCollection);
	uuYcDatasetParseId(*id, *idComponents);

	uuYcIntakeCheckGeneric(*root, *id, *toplevels, *isCollection);

	if (*idComponents."experiment_type" == "echo") {
		uuYcIntakeCheckEtEcho(*root, *id, *toplevels, *isCollection);
	}


	# Save the aggregated counts of #objects, #warnings, #errors on object level
        foreach (*toplevel in *toplevels) {
		uuYcIntakeGetAggregatedObjectCount(*id, *toplevel, *count);
                msiAddKeyVal(*kv, "object_count", str(*count));
                errorcode(msiAssociateKeyValuePairsToObj(*kv, *toplevel, if *isCollection then "-C" else "-d"));

		uuYcIntakeGetAggregatedObjectErrorCount(*toplevel, *count);
                msiAddKeyVal(*kv1, "object_errors", str(*count));
                errorcode(msiAssociateKeyValuePairsToObj(*kv1, *toplevel, if *isCollection then "-C" else "-d"));

		uuYcIntakeGetAggregatedObjectWarningCount(*toplevel, *count);
                msiAddKeyVal(*kv2, "object_warnings", str(*count));
                errorcode(msiAssociateKeyValuePairsToObj(*kv2, *toplevel, if *isCollection then "-C" else "-d"));
        }
}


uuYcIntakeGetAggregatedObjectCount(*datasetId, *tlCollection, *objects) {

      *objects = 0;
#      succeed;

      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME like "*tlCollection/%"
                                AND META_DATA_ATTR_NAME = "dataset_id"
                                AND META_DATA_ATTR_VALUE = "*datasetId"
              ){
         *objects = *objects + 1;
      }
      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME = "*tlCollection"
                                AND META_DATA_ATTR_NAME = "dataset_id"
                                AND META_DATA_ATTR_VALUE = "*datasetId"
              ){
         *objects = *objects + 1;
      }
}

uuYcIntakeGetAggregatedObjectWarningCount(*tlCollection, *objectWarnings) {

      *objectWarnings = 0;

      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME like "*tlCollection/%"
                                AND META_DATA_ATTR_NAME = "warning"
              ){
         *objectWarnings = *objectWarnings + 1;
      }

      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME = "*tlCollection"
                                AND META_DATA_ATTR_NAME = "warning"
              ){
         *objectWarnings = *objectWarnings + 1;
      }

      foreach (*coll in SELECT count(COLL_NAME)
                              WHERE COLL_NAME like "*tlCollection/%"
                                AND META_COLL_ATTR_NAME = "warning"
              ){
         *objectWarnings = *objectWarnings + int(*coll."COLL_NAME");
      }
}

uuYcIntakeGetAggregatedObjectErrorCount(*tlCollection, *objectErrors) {

      *objectErrors = 0;

      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME like "*tlCollection/%"
                                AND META_DATA_ATTR_NAME = "error"
              ){
         *objectErrors = *objectErrors + 1;
      }
      foreach (*dataFile in SELECT DATA_ID
                              WHERE COLL_NAME = "*tlCollection"
                                AND META_DATA_ATTR_NAME = "error"
              ){
         *objectErrors = *objectErrors + 1;
      }

      # also check subcollections for metadata e.g. illegal chars in name
      foreach (*coll in SELECT count(COLL_NAME)
                              WHERE COLL_NAME like "*tlCollection/%"
                                AND META_COLL_ATTR_NAME = "error"
              ){
         *objectErrors = *objectErrors + int(*coll."COLL_NAME");
      }      
}


# \brief Run checks on all datasets under *root.
#
# \param[in] root
#
uuYcIntakeCheckDatasets(*root) {
	uuYcDatasetGetIds(*root, *ids);
	foreach (*id in *ids) {
		uuYcDatasetIsLocked(*root, *id, *isLocked, *isFrozen);
		if (*isLocked || *isFrozen) {
			writeLine("stdout", "Skipping checks for dataset id <*id> (locked)");
		} else {
			writeLine("stdout", "Checking dataset id <*id>");
			uuYcIntakeCheckDataset(*root, *id);
		}
	}
}

# \brief Detect datasets under *root and check them.
#
# \param[in] root
#
uuYcIntakeScan(*root, *status) {

	*status = 1;

	# uuLock(*root, *lockStatus);
	# writeLine("stdout", "lockstatus: *lockStatus");
	*lockStatus = 0;

	if (*lockStatus == 0) {
		# Pre-define all used KVs to avoid hackery in uuKvExists().
		*scope."." = ".";

		# The dataset collection, or the first parent of a data-object dataset object.
		# Incorporated into the dataset_id.
		*scope."dataset_directory"    = ".";

		# Extracted WEPV, as found in pathname components.
		*scope."wave"            = ".";
		*scope."experiment_type" = ".";
		*scope."pseudocode"      = ".";
		*scope."version"         = ".";

                
		uuYcIntakeScanCollection(*root, *scope, false);
		uuYcIntakeCheckDatasets(*root);

		uuUnlock(*root);
		*status = 0;
	} else {
		*status = 2;
	}
}

# \brief Adds a comment to the dataset specified by *datasetId.
#
# \param[in] root
# \param[in] datasetId
# \param[in] message
#
uuYcIntakeCommentAdd(*root, *datasetId, *message) {
	msiGetIcatTime(*timestamp, "unix");
	*comment = "$userNameClient:*timestamp:*message";

	uuYcDatasetGetToplevelObjects(*root, *datasetId, *toplevelObjects, *isCollection);

	foreach (*toplevel in *toplevelObjects) {
		msiAddKeyVal(*kv, "comment", "*comment");
		errorcode(msiAssociateKeyValuePairsToObj(*kv, *toplevel, if *isCollection then "-C" else "-d"));
	}
}
