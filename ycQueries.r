# \file
# \brief     Youth Cohort - Dataset query related functions.
# \author    Ton Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

#test {
#  *root = "/nluu1a/home/grp-intake-vijfmnd";
#  *root = "/nluu1ot/home/grp-intake-youth";
#  uuYcDatasetGetIds(*root, *ids);
#  *total = size(*ids);
#  writeLine("stdout","found *total datasets");
#  *counter = 1;
#  foreach (*datasetId in *ids) { 
#   writeLine("stdout", "---- *counter ----------------------------");
#   *counter = *counter + 1; 
#   writeLine("stdout", "datasetId = *datasetId");
#   uuYcQueryDataset(*datasetId, *wave, *expType, *pseudocode, *version, 
#                      *datasetStatus, *datasetCreateName, *datasetCreateDate, 
#                      *datasetErrors, *datasetWarnings, *datasetComments,
#                      *objects, *objectErrors, *objectWarnings);
#   if (*datasetStatus == "locked" ) { 
#   if (*pseudocode == "A15234" ) {
#   writeLine("stdout", "wepv = *wave, *expType, *pseudocode, *version");
#   writeLine("stdout", "status = *datasetStatus, create = *datasetCreateName, date = *datasetCreateDate");
#   writeLine("stdout", "set errors/warnings/comments: *datasetErrors *datasetWarnings *datasetComments");
#   writeLine("stdout", "object errors/warnings/number: *objectErrors, *objectWarnings, *objects"); 
#   }
#   }
#}


# \brief query dataset overview information
#
# \param[in]  datasetid   unique id of the dataset
# \param[out] .... all other parameters, see below
# \param[out] datasetStatus  can have one of values: 'scanned','locked','frozen'

uuYcQueryDataset(*datasetId, *wave, *expType, *pseudocode, *version, 
                 *datasetStatus, *datasetCreateName, *datasetCreateDate, 
                 *datasetErrors, *datasetWarnings, *datasetComments,
                 *objects, *objectErrors, *objectWarnings
                ) {
   *datasetStatus   = "scanned";
   *datasetErrors   = 0;
   *datasetWarnings = 0;
   *datasetComments = 0;
   *objects         = 0;
   *objectErrors    = 0;
   *objectWarnings  = 0;
   *datasetCreateName = "==UNKNOWN==";
   *datasetCreateDate = 0;

   uuYcDatasetParseId(*datasetId, *idComponents);
   *wave       = *idComponents."wave";
   *expType    = *idComponents."experiment_type";
   *pseudocode = *idComponents."pseudocode";
   *version    = *idComponents."version";
   *directory  = *idComponents."directory";
   uuChopPath(*directory, *parent, *basename);
   uuYcDatasetGetToplevelObjects(*parent, *datasetId, *tlObjects, *isCollection);

   if (*isCollection) {
#      writeLine("stdout", "ISCOLLECTION");
      *tlCollection = elem(*tlObjects, 0);
      foreach (*row in SELECT COLL_NAME, COLL_OWNER_NAME, COLL_CREATE_TIME
                       WHERE COLL_NAME = "*tlCollection") {
         *datasetCreateName = *row."COLL_OWNER_NAME";
         *datasetCreateDate = *row."COLL_CREATE_TIME";
      }
      foreach (*row in SELECT COLL_NAME, META_COLL_ATTR_NAME, count(META_COLL_ATTR_VALUE)
                       WHERE COLL_NAME = "*tlCollection") {
         if (*row."META_COLL_ATTR_NAME" == "dataset_error") {
            *datasetErrors = *datasetErrors + int(*row."META_COLL_ATTR_VALUE");
         }
         if (*row."META_COLL_ATTR_NAME" == "dataset_warning") {
            *datasetWarnings = *datasetWarnings + int(*row."META_COLL_ATTR_VALUE");
         }
         if (*row."META_COLL_ATTR_NAME" == "comment") {
            *datasetComments = *datasetComments + int(*row."META_COLL_ATTR_VALUE");
         }
         if (*row."META_COLL_ATTR_NAME" == "to_vault_freeze") {
            *datasetStatus = "frozen";
         }
         if (*row."META_COLL_ATTR_NAME" == "to_vault_lock") {
            *datasetStatus = "locked";
         }
      }

      # Get the aggregated counts for nr of objects, object errors and object warnings
      foreach (*row in SELECT COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
                       WHERE COLL_NAME = "*tlCollection") {
         if (*row."META_COLL_ATTR_NAME" == "object_count") {
            *objects = *objects + int(*row."META_COLL_ATTR_VALUE");
         }
         if (*row."META_COLL_ATTR_NAME" == "object_errors") {
            *objectErrors = *objectErrors + int(*row."META_COLL_ATTR_VALUE");
         }
         if (*row."META_COLL_ATTR_NAME" == "object_warnings") {
            *objectWarnings = *objectWarnings + int(*row."META_COLL_ATTR_VALUE");
         }
      }
   }

   if (!*isCollection) {
#      writeLine("stdout","NOT A COLLECTION");
      foreach (*dataObject in *tlObjects) {
         uuChopPath(*dataObject, *parent, *basename);
         *objects = *objects + 1;
         if (*objects == 1) {
            foreach (*row in SELECT  DATA_OWNER_NAME, DATA_CREATE_TIME
                       WHERE DATA_NAME = "*basename"
                         AND COLL_NAME = "*parent" ) {
               *datasetCreateName = *row."DATA_OWNER_NAME";
               *datasetCreateDate = *row."DATA_CREATE_TIME";
            }
         }
         foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
                       WHERE DATA_NAME = "*basename"
                         AND COLL_NAME = "*parent") {
            if (*row."META_DATA_ATTR_NAME" == "error") {
               *objectErrors = *objectErrors + 1;
            }
            if (*row."META_DATA_ATTR_NAME" == "warning") {
               *objectWarnings = *objectWarnings + 1;
            }
            if (*objects == 1) {
               # dataset info is duplicated across objects, so count only once
              if (*row."META_DATA_ATTR_NAME" == "dataset_error") {
                  *datasetErrors = *datasetErrors + 1;
               }
               if (*row."META_DATA_ATTR_NAME" == "dataset_warning") {
                  *datasetWarnings = *datasetWarnings + 1;
               }
               if (*row."META_DATA_ATTR_NAME" == "comment") {
                  *datasetComments = *datasetComments + 1;
               }
            }
            if (*row."META_DATA_ATTR_NAME" == "to_vault_freeze") {
               *datasetStatus = "frozen";
            }
            if (*row."META_DATA_ATTR_NAME" == "to_vault_lock") {
               *datasetStatus = "locked";
            }
          
         } # end foreach row 
      } # end foreach dataObject
   } # end is not collection
      
}



#input null
#output ruleExecOut
