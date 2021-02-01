# \file      Makefile
# \brief     Makefile for building and installing the Utrecht University Yoda iRODS ruleset
# \author    Lazlo Westerhof
# \author    Paul Frederiks
# \author    Chris Smeele
# \copyright Copyright (c) 2015-2020, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.
#
# Please note the following:
#
# - To make use of the 'update' make target, this ruleset directory needs to
#   have a .git directory (i.e. you should clone this repository using git,
#   rather than download a source tarball).
#
# - The 'update' target simply does a git pull. Make sure to checkout the
#   correct branch for your environment first. That is, 'master' for a
#   production environment, 'release-*' for acceptance environments, and
#   'development' for dev/test environments.
#
# - For the 'install' make target to work, you should place this ruleset
#   directory in the folder '/etc/irods/'. Don't forget to
#   append the ruleset name ($RULESET_NAME minus the '.re' extension) to the
#   rulesets in /etc/irods/server_config.json, and to add the python ruleset
#   name to core.py.
#
# make update  - pull changes from git remote, updates .r files
# make install - install ruleset (concatenated .r files) into the parent directory

# Input files. Exclude all test rules in ./tests
PYRULE_FILES ?= $(sort $(wildcard uu*.py ii*.py))
RULE_FILES   ?= $(sort $(wildcard uu*.r  ii*.r yc*.r))

# Output files.
RULESET_NAME   ?= rules-uu.re
RULESET_FILE   := $(RULESET_NAME)
DEBUG_FILE     := $(RULESET_NAME).debug

INSTALL_DIR  ?= ..

# Make targets.
all: $(RULESET_FILE)

$(RULESET_FILE): $(RULE_FILES)
	cat $^ | sed '/^\s*\(#.*\)\?$$/d' > $@

install: $(RULESET_FILE)
	cp --backup $(RULESET_FILE) $(INSTALL_DIR)/$(RULESET_NAME)

clean:
	rm -f $(RULESET_FILE)

update:
	git pull

$(DEBUG_FILE): $(RULE_FILES)
	cat $^ | sed 's/#DEBUG\s//' | sed '/^\s*\(#.*\)\?$$/d' > $@

debug: $(DEBUG_FILE)

debug-install: $(DEBUG_FILE)
	cp --backup $< $(INSTALL_DIR)/$(RULESET_NAME)
