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

# Input files.

RULE_FILES ?= $(shell find . -type f -iname '*.r')

# Output files.

RULESET_NAME ?= rules-uu.re
RULESET_FILE := $(RULESET_NAME)

INSTALL_DIR  ?= ..

# Make targets.

all: $(RULESET_FILE)

$(RULESET_FILE): $(RULE_FILES)
	cat $(RULE_FILES) | sed '/^\s*\(#.*\)\?$$/d' > $(RULESET_FILE)

install: $(RULESET_FILE)
	cp --backup $(RULESET_FILE) $(INSTALL_DIR)/$(RULESET_NAME)

clean:
	rm -f $(RULESET_FILE)

update:
	git pull
