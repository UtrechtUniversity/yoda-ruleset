# \file      ycModule.r
# \brief     Youth Cohort module
# \copyright Copyright (c) 2016-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE


# \brief move all locked datasets to the vault
#
# \param[in]  intakeCollection  pathname root of intake area
# \param[in]  vaultCollection   pathname root of vault area
# \param[out] status            result of operation either "ok" or "error"
#
uuYc2Vault(*intakeRoot, *vaultRoot, *status) {
    *status = 0;
    rule_intake_to_vault(*intakeRoot, *vaultRoot);
}


# \brief (over)write data object with a list of vault object checksums
#
# \param[in]  vaultRoot          root collection to be indexed
# \param[in]  destinationObject  dataobject that will be written to
# \param[out] status             0 = success,  nonzero is error
uuYcGenerateDatasetsIndex(*vaultRoot, *destinationObject, *status) {
   *status = 0;
   msiDataObjCreate(*destinationObject, "forceFlag=", *FHANDLE);

   foreach (*row in SELECT COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE
                    WHERE COLL_NAME = "*vaultRoot" ) {
      *checksum = *row."DATA_CHECKSUM";
      *name     = *row."DATA_NAME";
      *col      = *row."COLL_NAME";
      *size     = *row."DATA_SIZE";
      uuChopChecksum(*checksum, *type, *checksumOut);
      *textLine = "*type *checksumOut *size *col/*name\n";
      msiStrlen(*textLine, *length);
      msiStrToBytesBuf(*textLine, *buffer);
      msiDataObjWrite(*FHANDLE, *buffer, *bytesWritten);
      if (int(*length) != *bytesWritten) then {
         *status = 1;
      }
   }
   foreach (*row in SELECT COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE
                    WHERE COLL_NAME like '*vaultRoot/%' ) {
      *checksum = *row."DATA_CHECKSUM";
      *name     = *row."DATA_NAME";
      *col      = *row."COLL_NAME";
      *size     = *row."DATA_SIZE";
      uuChopChecksum(*checksum, *type, *checksumOut);
      *textLine = "*type *checksumOut *size *col/*name\n";
      msiStrlen(*textLine, *length);
      msiStrToBytesBuf(*textLine, *buffer);
      msiDataObjWrite(*FHANDLE, *buffer, *bytesWritten);
      if (int(*length) != *bytesWritten) then {
         *status = 1;
      }
   }
   msiDataObjClose(*FHANDLE, *status2);
   *status;
}

# \brief Add a dataset warning to all given dataset toplevels.
#
# \param[in] toplevels
# \param[in] isCollectionToplevel
# \param[in] text
#
uuYcIntakeCheckAddDatasetWarning(*toplevels, *isCollectionToplevel, *text) {
	msiAddKeyVal(*kv, "dataset_warning", *text);

	foreach (*toplevel in *toplevels) {
		msiAssociateKeyValuePairsToObj(*kv, *toplevel, if *isCollectionToplevel then "-C" else "-d");
	}
}

# \brief Add a dataset error to all given dataset toplevels.
#
# \param[in] toplevels
# \param[in] isCollectionToplevel
# \param[in] text
#
uuYcIntakeCheckAddDatasetError(*toplevels, *isCollectionToplevel, *text) {
	msiAddKeyVal(*kv, "dataset_error", *text);

	foreach (*toplevel in *toplevels) {
		msiAssociateKeyValuePairsToObj(*kv, *toplevel, if *isCollectionToplevel then "-C" else "-d");
	}
}

# Reusable check utilities {{{

# \brief Check if a certain filename pattern has enough occurrences in a dataset.
#
# Adds a warning if the match count is out of range.
#
# NOTE: Currently, patterns must match the full relative object path.
#       At the time of writing, Echo is the only experiment type we run this
#       check for, and it is a flat dataset without subdirectories, so it makes
#       no difference there.
#
#       For other experiment types it may be desirable to match patterns with
#       basenames instead of paths. In this case the currently commented-out
#       code in this function can be used.
#
# \param[in] datasetParent        either the dataset collection or the first parent of a data-object dataset toplevel
# \param[in] toplevels            a list of toplevel objects
# \param[in] isCollectionToplevel
# \param[in] objects              a list of dataset object paths relative to the datasetParent parameter
# \param[in] patternHuman         a human-readable pattern (e.g.: 'I0000000.raw')
# \param[in] patternRegex         a regular expression that matches filenames (e.g.: 'I[0-9]{7}\.raw')
# \param[in] min                  the minimum amount of occurrences. set to -1 to disable minimum check.
# \param[in] max                  the maximum amount of occurrences. set to -1 to disable maximum check.
#
uuYcIntakeCheckFileCount(*datasetParent, *toplevels, *isCollectionToplevel, *objects, *patternHuman, *patternRegex, *min, *max) {
	*count = 0;
	foreach (*path in *objects) {
		*name = *path;

		#if (*path like "*/*") {
		#	# We might want to match basenames instead of paths relative to the dataset root.
		#	uuChopPath(*path, *parent, *name);
		#} else {
		#	*name = *path;
		#}
		if (*name like regex *patternRegex) {
			*count = *count + 1;
		}
	}

	if (*min != -1 && *count < *min) {
		uuYcIntakeCheckAddDatasetWarning(*toplevels, *isCollectionToplevel, "Expected at least *min files of type '*patternHuman', found *count");
	}
	if (*max != -1 && *count > *max) {
		uuYcIntakeCheckAddDatasetWarning(*toplevels, *isCollectionToplevel, "Expected at most *max files of type '*patternHuman', found *count");
	}
}

# }}}
# Generic checks {{{

# \brief Check if a dataset's wave is a valid one.
#
# \param[in] root
# \param[in] id                   the dataset id to check
# \param[in] toplevels            a list of toplevel objects for this dataset id
# \param[in] isCollectionToplevel
#
uuYcIntakeCheckWaveValidity(*root, *id, *toplevels, *isCollectionToplevel) {
	# Note: It might be cleaner to grab the wave metadata tag from the toplevel instead.
	uuYcDatasetParseId(*id, *idComponents);
	uuStrToLower(*idComponents."wave", *wave);

	*waves = list(
		"20w", "30w",
		"0m", "5m", "10m",
		"3y", "6y", "9y", "12y", "15y"
	);

	uuListContains(*waves, *wave, *waveIsValid);
	if (!*waveIsValid) {
		uuYcIntakeCheckAddDatasetError(*toplevels, *isCollectionToplevel, "The wave '*wave' is not in the list of accepted waves");
	}
}

# \brief Run checks that must be applied to all datasets regardless of WEPV values.
#
# Call any generic checks you make in this function.
#
# \param[in] root
# \param[in] id           the dataset id to check
# \param[in] toplevels    a list of toplevel objects for this dataset id
# \param[in] isCollection
#
uuYcIntakeCheckGeneric(*root, *id, *toplevels, *isCollection) {
	uuYcIntakeCheckWaveValidity(*root, *id, *toplevels, *isCollection);
}

# }}}
# Experiment type specific checks {{{
# Echo {{{

# \brief Run checks specific to the Echo experiment type.
#
# \param[in] root
# \param[in] id           the dataset id to check
# \param[in] toplevels    a list of toplevel objects for this dataset id
# \param[in] isCollection
#
uuYcIntakeCheckEtEcho(*root, *id, *toplevels, *isCollection) {
	if (*isCollection) {
		*datasetParent = elem(*toplevels, 0);
	} else {
		uuChopPath(elem(*toplevels, 0), *dataObjectParent, *dataObjectName);
		*datasetParent = *dataObjectParent;
	}

	uuYcDatasetGetDataObjectRelPaths(*root, *id, *objects);

	uuYcIntakeCheckFileCount(*datasetParent, *toplevels, *isCollection, *objects, ``I0000000.index.jpg``, ``(.*/)?I[0-9]{7}\.index\.jpe?g``, 13, -1);
	uuYcIntakeCheckFileCount(*datasetParent, *toplevels, *isCollection, *objects, ``I0000000.raw``,       ``(.*/)?I[0-9]{7}\.raw``,           7, -1);
	uuYcIntakeCheckFileCount(*datasetParent, *toplevels, *isCollection, *objects, ``I0000000.dcm``,       ``(.*/)?I[0-9]{7}\.dcm``,           6, -1);
	uuYcIntakeCheckFileCount(*datasetParent, *toplevels, *isCollection, *objects, ``I0000000.vol``,       ``(.*/)?I[0-9]{7}\.vol``,           6, -1);
}

# }}}
# }}}
