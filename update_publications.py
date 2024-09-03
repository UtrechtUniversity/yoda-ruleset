from irods_connect import create_irods_session
import ssl
from irods.models import Collection, CollectionMeta
import re
from publication import rule_update_publication

IRODS_SSL_CA_FILE = '/etc/ssl/certs/localhost_and_chain.crt'
IRODS_AUTH_SCHEME = 'PAM'
IRODS_CLIENT_OPTIONS_FOR_SSL = {
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_client_server_negotiation": "request_server_negotiation",
        "irods_ssl_ca_certificate_file": IRODS_SSL_CA_FILE,
        "irods_ssl_verify_server": "cert",
        "irods_encryption_key_size": 16,
        "irods_encryption_salt_size": 8,
        "irods_encryption_num_hash_rounds": 16,
        "irods_encryption_algorithm": "AES-256-CBC"
    }


config = {
    "IRODS_ICAT_HOSTNAME": 'combined.yoda.test',
    "IRODS_ICAT_PORT": '1247',
    "IRODS_DEFAULT_ZONE": 'tempZone',
    "IRODS_DEFAULT_RESC": 'irodsResc',
    "IRODS_SSL_CA_FILE": IRODS_SSL_CA_FILE,
    "IRODS_AUTH_SCHEME": IRODS_AUTH_SCHEME,
    "IRODS_CLIENT_OPTIONS_FOR_SSL": IRODS_CLIENT_OPTIONS_FOR_SSL,
    "IRODS_SESSION_OPTIONS": {
        'ssl_context' : ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH,
            cafile=IRODS_SSL_CA_FILE,
            capath=None,
            cadata=None,
        ),
        **IRODS_CLIENT_OPTIONS_FOR_SSL,
        'authentication_scheme': IRODS_AUTH_SCHEME,
        'application_name': 'yoda-portal'
    }
}

username = 'datamanager'
password = 'test'

def update_publications(session, updateDatacite="Yes", updateLandingpage="Yes", updateMOAI="Yes", package='*'):
    print(f"[UPDATE PUBLICATIONS] Start for {package}")
    packages_found = False
    query = (
        session.query(Collection.name)
        .filter(CollectionMeta.name == 'org_' + 'vault_status') 
        .filter(CollectionMeta.value == 'PUBLISHED')  
    )
    results = query.all()
    coll_names = [result[Collection.name] for result in results if '/home/vault-' in result[Collection.name]]
    for coll_name in coll_names:
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
    try:
        with create_irods_session(username, password, config) as session:
            print("Connected to iRODS successfully!")
            update_publications(session)
    except Exception as e:
        print(e)
        print('Could not connect')
        
if __name__ == '__main__':
    main()
