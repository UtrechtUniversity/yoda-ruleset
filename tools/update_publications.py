
from arb_update_resources import parse_args, get_irods_environment, setup_session
from irods.exception import NetworkException
from irods.models import Collection, CollectionMeta

def update_publications(session, updateDatacite="Yes", updateLandingpage="Yes", updateMOAI="Yes", package='*'):
    print(f"[UPDATE PUBLICATIONS] Start for {package}")
    with session:
        query = (
            session.query(Collection.name, CollectionMeta.name, CollectionMeta.value)  # Equivalent to selecting COLL_NAME
            .filter(CollectionMeta.name == 'org_' + 'vault_status')  # Equivalent to META_COLL_ATTR_NAME
            .filter(CollectionMeta.value == 'PUBLISHED')  # Equivalent to META_COLL_ATTR_VALUE
        )
        results = query.all()
        filtered_results = [result for result in results if result[Collection.name].startswith('/home/vault-')]
        for result in filtered_results:
            coll_name = result[0]
            
            if (package == '*' and re.match(r'/[^/]+/home/vault-.*', coll_name)) or (package != '*' and re.match(r'/[^/]+/home/vault-.*', coll_name) and coll_name == package):
                packages_found = True
                status, status_info = '', ''
                rule_update_publication(coll_name, update_datacite, update_landingpage, update_moai, status, status_info)
                print(f"{coll_name}: {status} {status_info}")
                
    if not packages_found:
        print(f"[UPDATE PUBLICATIONS] No packages found for {package}")
    else:
        print(f"[UPDATE PUBLICATIONS] Finished for {package}")

def main():
    args = parse_args()
    env = get_irods_environment()

    try:
        session = setup_session(env)
        update_publications(session)
    except NetworkException:
        print("Could not connect to iRODS sever ...")


if __name__ == '__main__':
    main()
