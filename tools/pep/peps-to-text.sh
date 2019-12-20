# usage: same as peps-to-csv.sh
#
# This variant produces human-readable output (assuming there's no wrapping) by
# expanding tabs.

./peps-to-csv.sh "$@" | column -ts"	" | sed 's/ *$//'
