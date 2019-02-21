Research module Rules and Policies for Yoda/iRODS
==========

NAME
----
irods-ruleset-research - Subset of rules and policies for iRODS based Yoda required for the yoda-portal-research module

DESCRIPTION
-----------
Yoda is configuration of an iRODS server for dataset management.
These rules are required on top of the rules-uu rules to use the Yoda Portal research module designed.

It consists of:
- Research module specific rules and policies

DEPENDENCIES
------------
- [irods-ruleset-uu](https://github.com/UtrechtUniversity/irods-ruleset-uu)
- [irods-uu-microservices](https://github.com/UtrechtUniversity/irods-uu-microservices)
- All dependencies of the above

INSTALLATION
-----------
1) On the iRODS server, become the iRODS user and navigate to ``/etc/irods``

2) Clone the repository.

3) Navigate to the directory this repository was cloned in

4) Checkout the target branch.

5) Use the make file to compile and install the rules: ``make install``

6) Add the generated `rules-research.re` (as well as the requisite `rules-uu.re`) to the `server_config.json` the _re_rulebase_set_, above `core` in `/etc/irods/server_config.json`:

```javascript
"re_rulebase_set": [
    {  "filename":  "rules-research" },
    {  "filename":  "rules-uu" },
    { "filename": "core"}
]
```

7) Install the default schema and formelements for the metadata form. The user needs to be a rodsadmin. If the default target resource "irodsResc" does not exist, add a *resc parameter.
```
$ irule -F ./tools/install-default-xml-for-metadata.r
# or
$ irule -F ./tools/install-default-xml-for-metadata.r '*resc="demoResc"'
```

8) Configure a cronjob under a rodsadmin account to copy datapackages to the vault. Example line for crontab -e:

```
*/2 * * * * /bin/irule -F /etc/irods/irods-ruleset-research/tools/copy-accepted-folders-to-vault.r >>$HOME/iRODS/server/log/job_copy-accepted-folder-to-vault.r 2>&1
```

LICENSE
-------
This project is licensed under the GPLv3 license.

The full license can be found in [LICENSE](LICENSE).

AUTHORS
-------
- [Paul Frederiks](https://github.com/pfrederiks)
- [Jan de Mooij](https://github.com/ajdemooij)
- [Lazlo Westerhof](https://github.com/lwesterhof)
