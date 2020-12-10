#!/bin/sh
# /Date: 2019-01-16
# /Functionality:
# /Find files within the dynamic area of an intake study that have errors and/or warnings at file level.
# /A check for errors/warnings is performed ONLY on file level. 
# /Errors that can be found on dataset-toplevel or on collection level within a dataset, are NOT reported

# /Parameters:
# /Study: Name of the study the export has to search 

# /Run with DatasetErrorsAndWarnins.sh script to have the export added to a csv file.

irule -F ExportDatasetErrorsAndWarnings.r "*studyParam='$1'" > DatasetErrorsAndWarnings.csv
