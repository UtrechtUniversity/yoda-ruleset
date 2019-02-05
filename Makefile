
# Makefile for building and installing the UU Youth Cohort iRODS ruleset.
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
#   directory in the folder 'iRODS/server/config/reConfigs'. Don't forget to
#   append the ruleset name ($RULESET_NAME minus the '.re' extension) to the
#   reRuleSet line in server/config/server.config.
#
# - This ruleset depends on Utrecht Univerity's irods-ruleset-uu ruleset.
#   Specify rules-uu *before* rules-yc in your server/config/server.config's
#   reRuleSet line.
#
# make update  - pull changes from git remote, updates .r files
# make install - install ruleset (concatenated .r files) into the parent directory

# Input files. Exclude all test rules in ./tests and tools

RULE_FILES ?= $(shell find . -path "./tests" -prune -o -path "./tools" -prune -o -type f -iname '*.r' -print)
PYRULE_FILES ?= $(shell find . -path "./tests" -prune -o -path "./tools" -prune -o -type f -iname 'ii*.py' -print)


# Output files.

RULESET_NAME ?= rules-dc.re
RULESET_FILE := $(RULESET_NAME)
DEBUG_FILE := $(RULESET_NAME).debug
PYRULESET_NAME ?= rules_dc.py
PYRULESET_FILE := $(PYRULESET_NAME)

INSTALL_DIR  ?= ..

# Make targets.

all: $(RULESET_FILE) $(PYRULESET_FILE)

$(RULESET_FILE): $(RULE_FILES)
	cat $(RULE_FILES) | sed '/^\s*\(#.*\)\?$$/d' > $(RULESET_FILE)

$(PYRULESET_FILE): $(PYRULE_FILES)
	cat $(PYRULE_FILES) > $(PYRULESET_FILE)

install: $(RULESET_FILE) $(PYRULESET_FILE)
	cp --backup $(RULESET_FILE) $(INSTALL_DIR)/$(RULESET_NAME)
	cp --backup $(PYRULESET_FILE) $(INSTALL_DIR)/$(PYRULESET_NAME)

clean:
	rm -f $(RULESET_FILE) $(PYRULESET_FILE)

update:
	git pull

$(DEBUG_FILE): $(RULE_FILES)
	cat $(RULE_FILES) | sed 's/#DEBUG\s//' | sed '/^\s*\(#.*\)\?$$/d' > $(DEBUG_FILE)

debug: $(DEBUG_FILE)

debug-install: $(DEBUG_FILE)
	cp --backup $(DEBUG_FILE) $(INSTALL_DIR)/$(RULESET_NAME)
