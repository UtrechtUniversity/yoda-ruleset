import genquery

def main(rule_args, callback, rei):
    package_statuses = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = 'org_vault_status' "
        "AND COLL_NAME not like '%/original'",
        genquery.AS_TUPLE,
        callback) 

    package_meta_versions = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = 'href' "
        "AND COLL_NAME not like '%/original'",
        genquery.AS_TUPLE,
        callback)

    metadata_objects = genquery.row_iterator(
        "COLL_NAME, DATA_NAME",
        "DATA_NAME like 'yoda-metadata%' "
        "AND COLL_NAME not like '%/original'",
        genquery.AS_TUPLE,
        callback)

    for (coll, status) in package_statuses:

        meta_version = None
        meta_ext = None
        for (coll_, meta_version_) in package_meta_versions:
            if coll == coll_:
                meta_version = meta_version_
                break

        for (coll_, metadata_obj) in metadata_objects:
            if coll == coll_:
                if metadata_obj.endswith('.json'):
                    meta_ext = 'JSON'
                elif metadata_obj.endswith('.xml'):
                    meta_ext = 'XML'

        callback.writeLine("stdout", "---------------------------")
        callback.writeLine("stdout", "Vault Package: {}".format(coll))
        callback.writeLine("stdout", "Metadata type: {}".format(meta_ext))
        callback.writeLine("stdout", "Metadata version: {}".format(meta_version))

    callback.writeLine("stdout", "---------------------------")
    

INPUT null
OUTPUT ruleExecOut
