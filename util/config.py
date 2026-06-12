"""Yoda ruleset configuration."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import inspect
import os
import re
from typing import Any, List, Tuple

# Config class {{{


class Config:
    """Stores configuration info, accessible through attributes (config.foo).

    Valid options are determined when the object is initialized
    Setting non-existent options raises an AttributeError.
    Accessing non-existent options raises an AttributeError as well.

    Examples:
      x = config.foo
      y = config.bar  # AttributeError if bar does not exist
    """

    def __init__(self, **kwargs: Any) -> None:
        """kwargs must contain all valid options and their default values."""
        default_values = self._get_default_values()
        self._items  = {**default_values, **kwargs}
        self._frozen = False
        self._quiet_mode = False   # Meant for unit tests
        self._loading_errors = []

    def _get_default_values(self):
        """Should return all valid configuration items and their default value."""
        return {"environment": None,
                "measure_coverage": False,
                "default_yoda_schema": None,
                "resource_primary": [],
                "resource_trigger_pol": [],
                "resource_repl_exempt": [],
                "resource_replica": [],
                "resource_research": None,
                "resource_vault": None,
                "notifications_enabled": False,
                "notifications_sender_email": None,
                "notifications_sender_name": None,
                "notifications_reply_to": None,
                "smtp_server": None,
                "smtp_username": None,
                "smtp_password": None,
                "smtp_auth": True,
                "smtp_starttls": True,
                "datacite_rest_api_url": None,
                "datacite_username": None,
                "datacite_password": None,
                "datacite_publisher": None,
                "datacite_tls_verify": True,
                "eus_api_fqdn": None,
                "eus_api_port": None,
                "eus_api_secret": None,
                "eus_api_tls_verify": True,
                "enable_deposit": False,
                "enable_open_search": False,
                "enable_inactivity_notification": False,
                "enable_datarequest": False,
                "enable_data_package_archive": False,
                "data_package_archive_fqdn": None,
                "data_package_archive_minimum": 0,
                "data_package_archive_maximum": 0,
                "data_package_archive_resource": None,
                "enable_data_package_reference": False,
                "enable_tokens": False,
                "inactivity_cutoff_months": 3,
                "token_database": None,
                "token_database_password": None,
                "token_length": 0,
                "token_lifetime": 0,
                "token_expiration_notification": 0,
                "enable_async_checksum": False,
                "async_checksum_delay_time": 0,
                "async_replication_delay_time": 0,
                "async_replication_max_rss": 1000000000,
                "async_revision_delay_time": 0,
                "async_revision_max_rss": 1000000000,
                "yoda_portal_fqdn": None,
                "epic_pid_enabled": False,
                "epic_url": None,
                "epic_handle_prefix": None,
                "epic_key": None,
                "epic_certificate": None,
                "temporary_files": [],
                "external_users_domain_filter": [],
                "remote_anonymous_access": [],
                "enable_sram": True,
                "sram_rest_api_url": None,
                "sram_api_key": None,
                "sram_service_entity_id": None,
                "sram_verbose_logging": False,
                "sram_tls_verify": True,
                "sram_co_default_label": None,
                "sram_co_logo": None,
                "sram_co_default_admins": [],
                "sram_external_users_co": None,
                "arb_enabled": False,
                "arb_exempt_resources": [],
                "arb_min_gb_free": 0,
                "arb_min_percent_free": 5,
                "text_file_extensions": [],
                "pregenerated_data_dir": None,
                "matomo_tracking_enabled": False,
                "matomo_counter_enabled": False,
                "matomo_server_fqdn": None,
                "matomo_site_id": 1,
                "vault_copy_backoff_time": 300,
                "vault_copy_max_retries": 5,
                "vault_copy_multithread_enabled": True,
                "user_max_connections_enabled": False,
                "user_max_connections_number": 4,
                "enable_nfs_resource": False,
                "deaccession_cooldown": 14}

    def _get_config_filename(self) -> str:
        return os.path.join(os.path.dirname(__file__), '../rules_uu.cfg')

    def _get_contents_config_file(self) -> List[Tuple[int, str]]:
        with open(self._get_config_filename()) as f:
            contents = list(enumerate(f))
        return contents

    def _load_config(self, config_lines: List[Tuple[int, str]]) -> None:
        for i, line in config_lines:
            line = line.strip()
            # Skip comments, whitespace lines.
            if line.startswith('#') or len(line) == 0:
                continue
            # Interpret {k = 'v'} and {k =}
            m = re.match(r"""^([\w_]+)\s*=\s*(?:'(.*)')?$""", line)
            if not m:
                error_message = 'Configuration syntax error at {} line {}'.format(self._get_config_filename(), i + 1)
                # We do not throw an exception here, because that would cause the rule engine to fail
                # completely with a generic error message (since config initialization is at
                # compile time). Instead, we store the error message here, then have the policies
                # log any error message once the session has been fully established.
                self._loading_errors.append(error_message)
                continue

            # List-type values are separated by whitespace.
            try:
                typ = type(getattr(self, m.group(1)))
            except AttributeError:
                typ = str

            if issubclass(typ, list):
                if m.group(2) is None:
                    error_message = 'Configuration syntax error at {} line {}'.format(self._get_config_filename(), i + 1)
                    self._loading_errors.append(error_message)
                    continue
                else:
                    setattr(self, m.group(1), m.group(2).split())
            elif issubclass(typ, bool):
                try:
                    setattr(self, m.group(1), {'true': True, 'false': False}[m.group(2)])
                except KeyError:
                    error_message = 'Configuration syntax error at {} line {}'.format(self._get_config_filename(), i + 1)
                    # We do not throw an exception here, because that would cause the rule engine to fail
                    # completely with an obscure generic error message (since config initialization is at
                    # compile time). Instead, we store the error message, then print warnings once the
                    # session has been initialized.
                    self._loading_errors.append(error_message)

            elif issubclass(typ, int):
                setattr(self, m.group(1), int(m.group(2)))
            else:
                setattr(self, *m.groups())

    def freeze(self) -> None:
        """Prevent further config changes via setattr."""
        self._frozen = True

    def is_initialized(self):
        return self._frozen

    def initialize(self):
        # Try to prevent (accidental) config changes.
        if self.is_initialized():
            # Don't log this to reduce log clutter.
            return

        if os.path.exists(self._get_config_filename()):
            config_file_contents = self._get_contents_config_file()
            self._load_config(config_file_contents)
        else:
            if not self._quiet_mode:
                print("Configuration file not found. Initializing default configuration.")

        self.freeze()

    def get_configuration_errors(self) -> List[str]:
        return self._loading_errors

    def __setattr__(self, k: str, v: int) -> None:
        if k.startswith('_'):
            return super().__setattr__(k, v)
        if self._frozen:
            if not self._quiet_mode:
                print('Ruleset configuration error: No config changes possible to \'{}\''.format(k))
            return
        if k not in self._items:
            error_message = 'Ruleset configuration error: No such config option: \'{}\''.format(k)
            self._loading_errors.append(error_message)
            if not self._quiet_mode:
                print(error_message)
            return
        # Set as config option.
        self._items[k] = v

    def __getattr__(self, k: str) -> str | int | bool | List:
        if k.startswith('_'):
            return super().__getattr__(k)

        try:
            return self._items[k]
        except KeyError:
            # py3: should become 'raise ... from e'
            raise AttributeError('Config item <{}> does not exist'.format(k))

    # Never dump config values, they may contain sensitive info.
    def __str__(self) -> str:
        return 'Config()'

    def __repr__(self) -> str:
        return 'Config()'

# }}}


config = Config()
if any("yoda-ruleset/unit-tests/test_" in frame_info.filename for frame_info in inspect.stack()):
    # If we are running in the context of unit tests, suppress any warning messages to
    # reduce clutter in the test output.
    config._quiet_mode = True
config.initialize()
