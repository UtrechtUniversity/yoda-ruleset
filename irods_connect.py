import logging
from irods.session import iRODSSession
from irods.exception import iRODSException, NetworkException

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_irods_session(username: str, password: str, config: dict) -> iRODSSession:
    """Create an iRODS session with the given username and password."""
    try:
        logger.debug("Attempting to create an iRODS session")
        
        irods = iRODSSession(
            host=config.get('IRODS_ICAT_HOSTNAME'),
            port=config.get('IRODS_ICAT_PORT'),
            user=username,
            password=password,
            zone=config.get('IRODS_DEFAULT_ZONE'),
            configure=True,
            **config.get('IRODS_SESSION_OPTIONS', {})
        )

        if config.get('INTAKE_ENABLED'):
            irods.connection_timeout = config.get('INTAKE_EXT_TIMEOUT', 120)

        _ = irods.server_version
        logger.debug(f"Connected to iRODS server: {irods.host}:{irods.port}")

        return irods

    except NetworkException as ne:
        logger.error("Network-related error when connecting to iRODS", exc_info=True)
        raise ne

    except iRODSException as e:
        logger.error("iRODS-related error when connecting to iRODS", exc_info=True)
        raise e

    except Exception as ex:
        logger.error("Unexpected error when connecting to iRODS", exc_info=True)
        raise ex

