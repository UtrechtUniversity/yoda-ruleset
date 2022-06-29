# \file      iiRevisions.r
# \brief     Revision management. Each new file or file modification creates
#            a timestamped backup file in the revision store.
# \author    Paul Frederiks
# \copyright Copyright (c) 2017-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Scheduled revision creation batch job.
#
# Creates revisions for all data objects marked with 'org_revision_scheduled' metadata.
#
# \param[in] verbose           whether to log verbose messages for troubleshooting (1: yes, 0: no)
uuRevisionBatch(*verbose) {
    rule_revision_batch(*verbose);
}


# \brief Calculate the unix timestamp for the end of the current day (Same as start of next day).   ## KAN WEG ##
#
# param[out] endOfCalendarDay		Timestamp of the end of the current day
#
iiRevisionCalculateEndOfCalendarDay(*endOfCalendarDay) {
		msiGetIcatTime(*timestamp, "unix"); # Get current Timestamp
		*bdY = timestrf(datetime(double(*timestamp)), "%b %d %Y"); # Generate string of current date (e.g. Jan 14 1982).

		*endofcalendarday_dt = datetime(*bdY ++ " 23:59:59"); # Append the last second of the day and convert to datetime
		*endofcalendarday_str = timestrf(*endofcalendarday_dt, "%s"); # Generate string of unix timestamp of the last second of the day
		*endOfCalendarDay =  double(*endofcalendarday_str) + 1.0; # Convert to double and add 1 second to get 00:00 of the next day
}

# Deze moet blijven
# \datatype iirevisioncandidate    Represents a revision with a timestamp with an double for the timestamp and a string for the DATA_ID.
#                                  A removed candidate is represented with an empty data constructor
data iirevisioncandidate =
	| iirevisioncandidate : double * string -> iirevisioncandidate
	| iirevisionremoved : iirevisioncandidate


# \brief iiRevisionListOfCollectionBeforeTimestamp   ## BLIJFT ##
#
# \param[in] collName      name of collection
# \param[in] timestamp     only revisions created before this timestamp will be returned
# \param[out] revisions    list of revisions
#
iiRevisionListOfCollectionBeforeTimestamp(*collName, *timestamp, *revisions) {
        *revisions = list();
        *originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
        foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE META_DATA_ATTR_NAME = *originalPathKey AND META_DATA_ATTR_VALUE LIKE '*collName/%') {
                *originalPath = *row.META_DATA_ATTR_VALUE;
                iiRevisionLastBefore(*originalPath, *timestamp, *revisionId);
                if (*revisionId != "") {
                        *revisions = cons(iirevisionwithpath(*revisionId, *originalPath), *revisions);
                }
        }
}

# \brief iiRevisionLastBefore   ## BLIJFT ##
#
# \param[in] path        original path
# \param[in] timestamp   the first revision before this timestamp will be returned
# \param[out] revisionId  ID of revision
#
iiRevisionLastBefore(*path, *timestamp, *revisionId) {
        *revisionId = "";
        iiRevisionCandidates(*path, *candidates);
        foreach(*candidate in *candidates) {
                iirevisioncandidate(*timeDouble, *candidateId) = *candidate;
                if (*timeDouble < *timestamp) {
                        *revisionId = *candidateId;
                        break;
                }
        }
}

# \brief Return list of revisioncandidates of a path.
#
# \param[in]  path       path of original
# \param[out] revisions  list of revisioncandidates
#
iiRevisionCandidates(*path, *revisions) {

	*revisions = list();
	*originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
	*revisionStore = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;

	foreach(*row in SELECT DATA_ID, order(DATA_NAME) WHERE META_DATA_ATTR_NAME = *originalPathKey
		                                         AND META_DATA_ATTR_VALUE = *path
							 AND COLL_NAME like "*revisionStore%") {
		*id = *row.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *mdkvp);
		msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
		*revisions = cons(iirevisioncandidate(double(*modifyTime), *id), *revisions);
	}
}

# \datatype iirevisionwithpath
# combination of revisionId and original path of the revised file
data iirevisionwithpath =
	| iirevisionwithpath : string * string -> iirevisionwithpath
