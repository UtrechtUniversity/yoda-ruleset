import genquery
import re

def main(rule_args, callback, rei):
    callback.writeLine("stdout", "[UPDATE PUBLICATIONS] Start for {}".format(global_vars))
    update_datacite = global_vars["*updateDatacite"]
    update_landingpage = global_vars["*updateLandingpage"]
    update_moai = global_vars["*updateMOAI"]
    package = global_vars["*package"].strip('"')

    callback.writeLine("stdout", "[UPDATE PUBLICATIONS] Start for {}".format(package))

    coll_names = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '%%/home/vault-%%' "
        "AND META_COLL_ATTR_NAME = 'org_vault_status' "
        "AND META_COLL_ATTR_VALUE = 'PUBLISHED'",
        genquery.AS_TUPLE,
        callback
    )

    packages_found = False
    for coll_name in coll_names:
        if ((package == '*' and re.match(r'/[^/]+/home/vault-.*', coll_name)) or (package != '*' and re.match(r'/[^/]+/home/vault-.*', coll_name) and coll_name == package)):
            packages_found = True
            status, status_info = '', ''
            res = callback.rule_update_publication(coll_name, update_datacite, update_landingpage, update_moai, status, status_info)
            callback.writeLine("stdout", "{}: {}".format(coll_name, res['arguments'][-2]))
            
    if not packages_found:
        callback.writeLine("stdout", "[UPDATE PUBLICATIONS] No packages found for {}".format(package))
    else:
        callback.writeLine("stdout", "[UPDATE PUBLICATIONS] Finished for {}".format(package))

input *updateDatacite="Yes", *updateLandingpage="Yes", *updateMOAI="Yes", *package="*"
output ruleExecOut
