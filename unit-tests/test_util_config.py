"""Unit tests for the Config object and configuration file parsing"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
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

    def _get_config(self, *args, **kwargs):
        config = Config(*args, **kwargs)
        config._quiet_mode = True
        return config

    # --- Config object basics -------------------------------------------------

    def test_defaults_are_populated(self):
        config = self._get_config()
        self.assertEqual(config.enable_sram, True)
        self.assertEqual(config.environment, None)
        self.assertEqual(config.resource_primary, [])
        self.assertEqual(config.token_length, 0)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_kwargs_override_defaults(self):
        config = self._get_config(environment='development')
        self.assertEqual(config.environment, 'development')
        # Options that were not passed keep their default.
        self.assertEqual(config.enable_sram, True)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_access_unknown_option_raises(self):
        config = self._get_config()
        with self.assertRaises(AttributeError):
            _ = config.does_not_exist

    def test_set_unknown_option_is_ignored(self):
        config = self._get_config()
        config.does_not_exist = 'value'  # ignored (only prints a warning)
        with self.assertRaises(AttributeError):
            _ = config.does_not_exist

    def test_set_known_option(self):
        config = self._get_config()
        config.environment = 'production'
        self.assertEqual(config.environment, 'production')
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_freeze_blocks_changes(self):
        config = self._get_config()
        self.assertFalse(config.is_initialized())
        config.freeze()
        self.assertTrue(config.is_initialized())
        config.environment = 'production'  # ignored once frozen
        self.assertEqual(config.environment, None)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    # --- _load_config: value parsing & type coercion --------------------------

    def test_parse_string_value(self):
        config = self._get_config()
        config._load_config(config_lines("environment = 'production'\n"))
        self.assertEqual(config.environment, 'production')
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_parse_empty_string_value_yields_none(self):
        # "key =" (no quoted value) sets a string option to None.
        config = self._get_config(default_yoda_schema='default-3')
        config._load_config(config_lines("default_yoda_schema =\n"))
        self.assertIsNone(config.default_yoda_schema)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_parse_bool_true_and_false(self):
        config = self._get_config()
        config._load_config(config_lines("enable_sram = 'false'\nenable_tokens = 'true'\n"))
        self.assertIs(config.enable_sram, False)
        self.assertIs(config.enable_tokens, True)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_parse_int_value(self):
        config = self._get_config()
        config._load_config(config_lines("token_length = '32'\n"))
        self.assertEqual(config.token_length, 32)
        self.assertIsInstance(config.token_length, int)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_parse_list_value(self):
        config = self._get_config()
        config._load_config(config_lines("resource_primary = 'irodsResc1 irodsResc2 irodsResc3'\n"))
        self.assertEqual(config.resource_primary, ['irodsResc1', 'irodsResc2', 'irodsResc3'])
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_whitespace_around_equals_is_tolerated(self):
        config = self._get_config()
        config._load_config(config_lines("environment   =    'production'\n"))
        self.assertEqual(config.environment, 'production')
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_multiple_options_in_one_pass(self):
        config = self._get_config()
        config._load_config(config_lines(
            "environment = 'production'\n"
            "enable_sram = 'false'\n"
            "token_length = '16'\n"
            "resource_primary = 'resc1 resc2'\n"
        ))
        self.assertEqual(config.environment, 'production')
        self.assertIs(config.enable_sram, False)
        self.assertEqual(config.token_length, 16)
        self.assertEqual(config.resource_primary, ['resc1', 'resc2'])
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_load_config_mutates_only_the_instance(self):
        # Parsing must not leak into a second, independent Config instance.
        config_a = self._get_config()
        config_b = self._get_config()
        config_a._load_config(config_lines("environment = 'production'\n"))
        self.assertEqual(config_a.environment, 'production')
        self.assertIsNone(config_b.environment)
        self.assertEqual(len(config_a.get_configuration_errors()), 0)
        self.assertEqual(len(config_b.get_configuration_errors()), 0)

    # --- _load_config: skipping & ignoring ------------------------------------

    def test_comments_and_blank_lines_are_skipped(self):
        config = self._get_config()
        config._load_config(config_lines(
            "# this is a comment\n"
            "\n"
            "   \n"
            "environment = 'production'\n"
            "# enable_sram = 'false'\n"
        ))
        self.assertEqual(config.environment, 'production')
        # The commented-out option keeps its default.
        self.assertIs(config.enable_sram, True)
        self.assertEqual(len(config.get_configuration_errors()), 0)

    def test_unknown_option_error_detected(self):
        config = self._get_config()
        # Unknown keys parse fine (type falls back to str) but setattr drops them.
        config._load_config(config_lines("not_a_real_option = 'whatever'\n"))
        with self.assertRaises(AttributeError):
            _ = config.not_a_real_option
        self.assertEqual(len(config.get_configuration_errors()), 1)

    # --- _load_config: error handling -----------------------------------------

    def test_no_equals_sign_error_detected(self):
        config = self._get_config()
        config._load_config(config_lines("this line has no equals sign\n"))
        self.assertEqual(len(config.get_configuration_errors()), 1)

    def test_string_no_opening_quote_error_detected(self):
        config = self._get_config()
        config._load_config(config_lines("environment = development'\n"))
        self.assertEqual(len(config.get_configuration_errors()), 1)

    def test_string_no_trailing_quote_error_detected(self):
        config = self._get_config()
        config._load_config(config_lines("environment = 'development\n"))
        self.assertEqual(len(config.get_configuration_errors()), 1)

    def test_string_no_quotes_error_detected(self):
        config = self._get_config()
        config._load_config(config_lines("environment = development\n"))
        self.assertEqual(len(config.get_configuration_errors()), 1)

    def test_invalid_bool_value_error_detected(self):
        config = self._get_config()
        config._load_config(config_lines("enable_sram = 'yes'\n"))
        self.assertEqual(len(config.get_configuration_errors()), 1)

    def test_empty_value_for_list_option_detected(self):
        config = self._get_config()
        config._load_config(config_lines("resource_primary =\n"))
        # Not a valid line, so default value is retained.
        self.assertEqual(config.resource_primary, [])
        # But an error is logged
        self.assertEqual(len(config.get_configuration_errors()), 1)
