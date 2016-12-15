# \brief orderclause	helper functions to determine order clause
# \param[in] column	Column to check
# \param[in] orderby	The column to orderby
# \param[in] ascdesc	"asc" for ascending order, "desc" for descending order. Defaults to Ascending
# \returnvalue		Returns either "" for no ordering, "ORDER_DESC" or "ORDER" when column needs ordering
uuorderclause(*column, *orderby, *ascdesc) = if *column == *orderby then uuorderdirection(*ascdesc) else ""
uuorderdirection(*ascdesc) = if *ascdesc == "desc" then "ORDER_DESC" else "ORDER"

uuiscollection(*collectionOrDataObject) = if *collectionOrDataObject == "Collection" then true else false

# \datatype	uucondition
# \description  a triple of strings to represent the elements of a condition query
# \constructor uucondition	Construct new conditions with condition(*column, *operator, *expression)	
data uucondition =
	| uucondition : string * string * string -> uucondition

# \function uumakelikecondition	Helper function to crete the most used condition
# \param[in] column		The irods column to search
# \param[in] searchstring	Part of the string to search on.
uumakelikecondition(*column, *searchstring) = uucondition(*column, "like", "%%*searchstring%%")

