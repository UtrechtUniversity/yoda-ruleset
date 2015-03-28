# Makefile to build and install iRODS ruleset
# 
# Please note the following:
# - the directory in which this makefile resides should have been
#   created via a "git clone" command (or something similar) referencing a 
#   repository master branch that will always provide a working release
#   (e.g. latest production release)
#
# - it relies on parent directory being: ../server/config/reConfigs
#   and the ruleset (see filename defined in RULESET variable) incuded
#   in the ruleset list in file ../server/config/server.config 
# 
#   make upgrade   - download latest release from origin git repository
#   make install   - combine rules and copy it to the "reConfigs" dir
#   make all       - all of the above
#

RULESET = rules-uu.re

all : upgrade install

install : ../$(RULESET)
	
../$(RULESET) : $(RULESET)
	cp --backup $(RULESET) ..

$(RULESET) : *.r
	cat *.r |sed '/^\t*#.*$$/d' > $(RULESET)

upgrade:
	git pull

clean :
	rm $(RULESET)

