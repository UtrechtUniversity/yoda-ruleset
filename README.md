Rules and Policies for Yoda/iRODS
=================================

NAME
----
ruleset-uu - all rules and policies to be configured with all Yoda iRODS environments

DESCRIPTION
-----------
Yoda is a configuration of an iRODS server for dataset management.

It consists of:
- General purpose rules and policies
- Research group or faculty specific rules and policies

This ruleset only contains functions and routines useful for all environments. Additional
rulesets need to be loaded for to fully configure a environment.

DEPENDENCIES
------------
- [irods > 4.1.8](https://irods.org/download/)
- [sudo microservices](https://github.com/UtrechtUniversity/irods-sudo-microservices) 
- [uu microservices](https://github.com/UtrechtUniversity/irods-uu-microservices)

INSTALLATION
-----------
1) On the iRODS server, become the iRODS user and navigate to ``/etc/irods``

2) Clone the repository.

3) Navigate to the directory this repository was cloned in

4) Checkout the target branch.

5) Use the make file to compile and install the rules: ``make install``

6) Add the generated `rules-uu.re` to the `server_config.json` the _re_rulebase_set_, above `core` in `/etc/irods/server_config.json`:

```javascript
"re_rulebase_set": [
    { "filename":  "rules-uu" },
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
*/2 * * * * /bin/irule -F /etc/irods/irods-ruleset-uu/tools/copy-accepted-folders-to-vault.r >>$HOME/iRODS/server/log/job_copy-accepted-folder-to-vault.r 2>&1
```

LICENSE
-------
This project is licensed under the GPLv3 license.

The full license can be found in [LICENSE](LICENSE).

AUTHORS
-------
- [Ton Smeele](https://github.com/tsmeele)
- [Chris Smeele](https://github.com/cjsmeele)
- [Paul Frederiks](https://github.com/pfrederiks)
- [Jan de Mooij](https://github.com/ajdemooij)
- [Lazlo Westerhof](https://github.com/lwesterhof)
- [Felix Croes](https://github.com/dworkin)
- [Harm de Raaff](https://github.com/HarmdR)
