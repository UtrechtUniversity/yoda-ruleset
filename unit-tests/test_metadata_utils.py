"""Unit tests for metadata functions"""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import sys
from unittest import TestCase

sys.path.append('../util')

from metadata_utils import get_json_metadata_errors, humanize_validation_error


class MetadataUtilsTest(TestCase):
    SAMPLE_SCHEMA = """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "title": {
      "type": "string"
    },
    "author": {
      "type": "string"
    },
    "medium": {
     "type": "string",
     "enum": ["book", "film"]
    }
  },
  "required": ["title", "author"],
  "additionalProperties": false
}
   """
    SAMPLE_SCHEMA_UNEVALUATED_PROPERTIES = """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "title": {
      "type": "string"
    },
    "author": {
      "type": "string"
    },
    "medium": {
     "type": "string",
     "enum": ["book", "film"]
    }
  },
  "required": ["title", "author"],
  "unevaluatedProperties": false
}
   """

    def test_get_json_metadata_errors_correct(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [])

    def test_get_json_metadata_errors_missing_element(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "'author' is a required property",
             'path': [],
             'schema_path': ['required'],
             'validator': 'required'}
        ])
        self.assertEqual(humanize_validation_error(errors[0]),
                         'This field is missing: author')

    def test_get_json_metadata_errors_missing_element_ignore_required(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          True
                                          )
        self.assertEqual(errors, [])

    def test_get_json_metadata_errors_extra_element(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan", "year": 1915}'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "Additional properties are not allowed ('year' was unexpected)",
             'path': [],
             'schema_path': ['additionalProperties'],
             'validator': 'additionalProperties'}
        ])
        self.assertEqual(humanize_validation_error(errors[0]),
                         'This extra field is not allowed: year')

    def test_get_json_metadata_errors_extra_element_unevaluated(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan", "year": 1915}'),
                                          json.loads(self.SAMPLE_SCHEMA_UNEVALUATED_PROPERTIES),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "Unevaluated properties are not allowed ('year' was unexpected)",
             'path': [],
             'schema_path': ['unevaluatedProperties'],
             'validator': 'unevaluatedProperties'}
        ])
        self.assertEqual(humanize_validation_error(errors[0]),
                         'This extra field is not allowed: year')

    def test_get_json_metadata_errors_extra_elements(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan", "year": 1915, "protagonist": "Richard Hannay"}'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "Additional properties are not allowed ('protagonist', 'year' were unexpected)",
             'path': [],
             'schema_path': ['additionalProperties'],
             'validator': 'additionalProperties'}
        ])
        self.assertEqual(humanize_validation_error(errors[0]),
                         "These extra fields are not allowed: 'protagonist', 'year'")

    def test_get_json_metadata_errors_wrong_element_name(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "writer": "John Buchan" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "'author' is a required property",
             'path': [],
             'schema_path': ['required'],
             'validator': 'required'},
            {'message': "Additional properties are not allowed ('writer' was unexpected)",
             'path': [],
             'schema_path': ['additionalProperties'],
             'validator': 'additionalProperties'},
        ])

    def test_get_json_metadata_errors_good_enum(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan", "medium": "book" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [])

    def test_get_json_metadata_errors_bad_enum(self):
        errors = get_json_metadata_errors(None,
                                          '',
                                          json.loads('{ "title": "The Thirty-Nine Steps", "author": "John Buchan", "medium": "novel" }'),
                                          json.loads(self.SAMPLE_SCHEMA),
                                          False
                                          )
        self.assertEqual(errors, [
            {'message': "'novel' is not one of ['book', 'film']",
             'path': ['medium'],
             'schema_path': ['properties', 'medium', 'enum'],
             'validator': 'enum'}
        ])
        self.assertEqual(humanize_validation_error(errors[0]),
                         'This field contains an error: medium')
