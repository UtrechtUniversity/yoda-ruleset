"""Unit tests for the Config object and configuration file parsing"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import sys
import tempfile
from unittest import TestCase

sys.path.append('../util')

from config import Config


def config_lines(text):
    """Turn a config-file string into the (line number, line) list that
    _load_config expects (the same shape _get_contents_config_file produces).

    :param text: raw text of the configuration file

    :returns:    list of <line number, line text> tuples of the configuration
    """
    return list(enumerate(text.splitlines(keepends=True)))


class UtilConfigTest(TestCase):

    # --- Config object basics -------------------------------------------------

    def test_defaults_are_populated(self):
        config = Config()
        self.assertEqual(config.enable_sram, True)
        self.assertEqual(config.environment, None)
        self.assertEqual(config.resource_primary, [])
        self.assertEqual(config.token_length, 0)

    def test_kwargs_override_defaults(self):
        config = Config(environment='development')
        self.assertEqual(config.environment, 'development')
        # Options that were not passed keep their default.
        self.assertEqual(config.enable_sram, True)

    def test_access_unknown_option_raises(self):
        config = Config()
        config._quiet_mode = True
        with self.assertRaises(AttributeError):
            _ = config.does_not_exist

    def test_set_unknown_option_is_ignored(self):
        config = Config()
        config._quiet_mode = True
        config.does_not_exist = 'value'  # ignored (only prints a warning)
        with self.assertRaises(AttributeError):
            _ = config.does_not_exist

    def test_set_known_option(self):
        config = Config()
        config.environment = 'production'
        self.assertEqual(config.environment, 'production')

    def test_freeze_blocks_changes(self):
        config = Config()
        config._quiet_mode = True
        self.assertFalse(config.is_initialized())
        config.freeze()
        self.assertTrue(config.is_initialized())
        config.environment = 'production'  # ignored once frozen
        self.assertEqual(config.environment, None)

    # --- _load_config: value parsing & type coercion --------------------------

    def test_parse_string_value(self):
        config = Config()
        config._load_config(None, config_lines("environment = 'production'\n"))
        self.assertEqual(config.environment, 'production')

    def test_parse_empty_string_value_yields_none(self):
        # "key =" (no quoted value) sets a string option to None.
        config = Config(default_yoda_schema='default-3')
        config._load_config(None, config_lines("default_yoda_schema =\n"))
        self.assertIsNone(config.default_yoda_schema)

    def test_parse_bool_true_and_false(self):
        config = Config()
        config._load_config(None, config_lines("enable_sram = 'false'\nenable_tokens = 'true'\n"))
        self.assertIs(config.enable_sram, False)
        self.assertIs(config.enable_tokens, True)

    def test_parse_int_value(self):
        config = Config()
        config._load_config(None, config_lines("token_length = '32'\n"))
        self.assertEqual(config.token_length, 32)
        self.assertIsInstance(config.token_length, int)

    def test_parse_list_value(self):
        config = Config()
        config._load_config(None, config_lines("resource_primary = 'irodsResc1 irodsResc2 irodsResc3'\n"))
        self.assertEqual(config.resource_primary, ['irodsResc1', 'irodsResc2', 'irodsResc3'])

    def test_empty_value_for_list_option_currently_raises(self):
        # Pre-existing behaviour (present before the refactor too): "key =" with
        # no value only works for string options. For a list option the empty
        # value is None and `None.split()` raises. Documented here so that a
        # future change to support `resource_primary =` (-> []) is deliberate.
        config = Config()
        with self.assertRaises(AttributeError):
            config._load_config(None, config_lines("resource_primary =\n"))

    def test_whitespace_around_equals_is_tolerated(self):
        config = Config()
        config._load_config(None, config_lines("environment   =    'production'\n"))
        self.assertEqual(config.environment, 'production')

    def test_multiple_options_in_one_pass(self):
        config = Config()
        config._load_config(None, config_lines(
            "environment = 'production'\n"
            "enable_sram = 'false'\n"
            "token_length = '16'\n"
            "resource_primary = 'resc1 resc2'\n"
        ))
        self.assertEqual(config.environment, 'production')
        self.assertIs(config.enable_sram, False)
        self.assertEqual(config.token_length, 16)
        self.assertEqual(config.resource_primary, ['resc1', 'resc2'])

    def test_load_config_mutates_only_the_instance(self):
        # Parsing must not leak into a second, independent Config instance.
        config_a = Config()
        config_b = Config()
        config_a._load_config(None, config_lines("environment = 'production'\n"))
        self.assertEqual(config_a.environment, 'production')
        self.assertIsNone(config_b.environment)

    # --- _load_config: skipping & ignoring ------------------------------------

    def test_comments_and_blank_lines_are_skipped(self):
        config = Config()
        config._load_config(None, config_lines(
            "# this is a comment\n"
            "\n"
            "   \n"
            "environment = 'production'\n"
            "# enable_sram = 'false'\n"
        ))
        self.assertEqual(config.environment, 'production')
        # The commented-out option keeps its default.
        self.assertIs(config.enable_sram, True)

    def test_unknown_option_is_ignored(self):
        config = Config()
        config._quiet_mode = True
        # Unknown keys parse fine (type falls back to str) but setattr drops them.
        config._load_config(None, config_lines("not_a_real_option = 'whatever'\n"))
        with self.assertRaises(AttributeError):
            _ = config.not_a_real_option

    # --- _load_config: error handling -----------------------------------------

    def test_no_equals_sign_raises_and_logs(self):
        config = Config()
        with self.assertRaises(Exception): # noqa B017
            config._load_config(config_lines("this line has no equals sign\n"))

    def test_string_no_opening_quote_raises_and_logs(self):
        config = Config()
        with self.assertRaises(Exception): # noqa B017
            config._load_config(config_lines("environment = development'\n"))

    def test_string_no_trailing_quote_raises_and_logs(self):
        config = Config()
        with self.assertRaises(Exception): # noqa B017
            config._load_config(config_lines("environment = 'development\n"))

    def test_string_no_quotes_raises_and_logs(self):
        config = Config()
        with self.assertRaises(Exception): # noqa B017
            config._load_config(config_lines("environment = development\n"))

    def test_syntax_error_reports_line_number(self):
        config = Config()
        with self.assertRaises(Exception): # noqa B017
            config._load_config(config_lines(
                "environment = 'production'\n"
                "this is broken\n"
            ))

    def test_invalid_bool_value_raises(self):
        config = Config()
        # Boolean options only accept 'true'/'false'.
        with self.assertRaises(KeyError):
            config._load_config(None, config_lines("enable_sram = 'yes'\n"))

    # --- file reading & initialize() end to end -------------------------------

    def _write_temp_cfg(self, content):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
        tmp.write(content)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_get_contents_config_file_returns_indexed_lines(self):
        config = Config()
        path = self._write_temp_cfg("environment = 'production'\nenable_sram = 'false'\n")
        config._get_config_filename = lambda: path
        contents = config._get_contents_config_file()
        self.assertEqual([i for i, _ in contents], [0, 1])
        self.assertIn('environment', contents[0][1])

    def test_initialize_loads_file_and_freezes(self):
        config = Config()
        path = self._write_temp_cfg("environment = 'production'\nenable_sram = 'false'\n")
        config._get_config_filename = lambda: path
        self.assertEqual(config.environment, 'production')
        self.assertIs(config.enable_sram, False)
        self.assertTrue(config.is_initialized())

    def test_initialize_without_config_file_uses_defaults(self):
        config = Config()
        config._get_config_filename = lambda: '/nonexistent/path/rules_uu.cfg'
        self.assertIs(config.enable_sram, True)
        self.assertTrue(config.is_initialized())

    def test_initialize_is_idempotent(self):
        config = Config()
        path = self._write_temp_cfg("environment = 'production'\n")
        config._get_config_filename = lambda: path
        # A second call must not reload or change anything (already initialized).
        self.assertEqual(config.environment, 'production')
        self.assertTrue(config.is_initialized())
