"""Yoda core ruleset containing iRODS and Python rules and policies useful for all Yoda environments."""

__version__   = '2.1.0'
__copyright__ = 'Copyright (c) 2015-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__author__    =  ('Felix Croes'
              + ', Roy van Elk'
              + ', Paul Frederiks'
              + ', Dylan Fu'
              + ', Rick van de Hoef'
              + ', Sirjan Kaur'
              + ', Costanza Laudisa'
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

import sys
sys.path.extend([ '/etc/irods/rules_uu', '/etc/irods/rules_uu/util' ])

# Import all modules containing rules into the package namespace,
# so that they become visible to iRODS.

from admin                    import *
from arb                      import *
from browse                   import *
from checksums                import *
from datacite                 import *
from exceptions               import *
from folder                   import *
from groups                   import *
from integration_tests        import *
from json_datacite            import *
from json_landing_page        import *
from mail                     import *
from meta                     import *
from meta_form                import *
from notifications            import *
from policies                 import *
from provenance               import *
from publication              import *
from publication_troubleshoot import *
from replication              import *
from research                 import *
from revisions                import *
from schema                   import *
from schema_transformation    import *
from schema_transformations   import *
from settings                 import *
from stats                    import *
from vault                    import *
from vault_deaccession        import *
from epic                     import *

# Import certain modules only when enabled.
if config.enable_datarequest:
    from datarequest import *

if config.enable_deposit:
    from deposit import *

if config.enable_tokens:
    from data_access_token import *

if config.enable_data_package_archive:
    from vault_archive import *
