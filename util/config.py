# -*- coding: utf-8 -*-
"""Yoda ruleset configuration."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


# Config class {{{

class Config(object):
    """Stores configuration info, accessible through attributes (config.foo).

    Valid options are determined at __init__ time.
    Setting non-existent options raises an AttributeError.
    Accessing non-existent options raises an AttributeError as well.

    Example:

      config = Config(foo = 'stuff')
      config.foo = 'other stuff'

      x = config.foo
      y = config.bar  # AttributeError
    """

    def __init__(self, **kwargs):
        """kwargs must contain all valid options and their default values."""
        self._items  = kwargs
        self._frozen = False

    def freeze(self):
        """Prevent further config changes via setattr."""
        self._frozen = True

    def __setattr__(self, k, v):
        if k.startswith('_'):
            return super(Config, self).__setattr__(k, v)
        if self._frozen:
            print('Ruleset configuration error: No config changes possible to \'{}\''.format(k))
            return
        if k not in self._items:
            print('Ruleset configuration error: No such config option: \'{}\''.format(k))
            return
        # Set as config option.
        self._items[k] = v

    def __getattr__(self, k):
        if k.startswith('_'):
            return super(Config, self).__getattr__(k)
        try:
            return self._items[k]
        except KeyError as e:
            # py3: should become 'raise ... from e'
            raise AttributeError('Config item <{}> does not exist'.format(k))

    # Never dump config values, they may contain sensitive info.
    def __str__(self):
        return 'Config()'

    def __repr__(self):
        return 'Config()'

    # def __repr__(self):
    #     return 'Config(\n{})'.format(''.join('  {} = {},\n'.format(k,
    #                 ('\n  '.join(repr(v).splitlines()) if isinstance(v, Config) else repr(v)))
    #                     for k, v in self._items.items()))

# }}}


# Default config {{{

# Note: Must name all valid config items.
config = Config(environment=None,
                resource_primary=[],
                resource_replica=None,
                notifications_enabled=False,
                notifications_sender_email=None,
                notifications_sender_name=None,
                notifications_reply_to=None,
                smtp_server=None,
                smtp_username=None,
                smtp_password=None,
                datacite_url=None,
                datacite_username=None,
                datacite_password=None,
                eus_api_fqdn=None,
                eus_api_port=None,
                eus_api_secret=None,
                enable_intake=False,
                enable_datarequest=False,
                yoda_portal_fqdn=None,
                epic_pid_enabled=False,
                epic_url=None,
                epic_handle_prefix=None,
                epic_key=None,
                epic_certificate=None)

# }}}

# Optionally include a site-local config file to override the above.
# (note: this is done only once per agent)
try:
    import os
    import re
    # Look for a config file in the root dir of this ruleset.
    cfgpath = os.path.dirname(__file__) + '/../rules_uu.cfg'
    with open(cfgpath) as f:
        for i, line in enumerate(f):
            line = line.strip()
            # Skip comments, whitespace lines.
            if line.startswith('#') or len(line) == 0:
                continue
            # Interpret {k = 'v'} and {k =}
            m = re.match(r"""^([\w_]+)\s*=\s*(?:'(.*)')?$""", line)
            if not m:
                raise Exception('Configuration syntax error at {} line {}', cfgpath, i + 1)

            # List-type values are separated by whitespace.
            try:
                typ = type(getattr(config, m.group(1)))
            except AttributeError as e:
                typ = str

            if issubclass(typ, list):
                setattr(config, m.group(1), m.group(2).split())
            elif issubclass(typ, bool):
                setattr(config, m.group(1), {'true': True, 'false': False}[m.group(2)])
            elif issubclass(typ, int):
                setattr(config, m.group(1), int(m.group(2)))
            else:
                setattr(config, *m.groups())

except IOError:
    # Ignore, config file is optional.
    pass

# Try to prevent (accidental) config changes.
config.freeze()
