# -*- coding: utf-8 -*-
"""Yoda core ruleset containing iRODS and Python rules and policies useful for all Yoda environments."""

__version__   = '1.10.0'
__copyright__ = 'Copyright (c) 2015-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__author__    =  ('Felix Croes'
              + ', Roy van Elk'
              + ', Paul Frederiks'
              + ', Dylan Fu'
              + ', Rick van de Hoef'
              + ', Sirjan Kaur'
              + ', Jan de Mooij'
              + ', Harm de Raaff'
              + ', Joris de Ruiter'
              + ', Claire Saliers'
              + ', Chris Smeele'
              + ', Ton Smeele'
              + ', Sietse Snel'
              + ', Leonidas Triantafyllou'
              + ', Lazlo Westerhof'
              + ', Jelmer Zondergeld')
# (in alphabetical order)

# Import all modules containing rules into the package namespace,
# so that they become visible to iRODS.

from admin                    import *
from browse                   import *
from folder                   import *
from groups                   import *
from json_datacite            import *
from json_landing_page        import *
from mail                     import *
from meta                     import *
from meta_form                import *
from provenance               import *
from research                 import *
from resources                import *
from schema                   import *
from schema_transformation    import *
from schema_transformations   import *
from publication_troubleshoot import *
from vault                    import *
from datacite                 import *
from epic                     import *
from publication              import *
from policies                 import *
from replication              import *
from revisions                import *
from settings                 import *
from notifications            import *
from integration_tests        import *

# Import certain modules only when enabled.
from .util.config import config

if config.enable_intake:
    from intake import *
    from intake_vault import *

if config.enable_datarequest:
    from datarequest import *

if config.enable_deposit:
    from deposit import *

if config.enable_tokens:
    from data_access_token import *

if config.enable_data_package_archive:
    from vault_archive import *

if config.enable_data_package_download:
    from vault_download import *
