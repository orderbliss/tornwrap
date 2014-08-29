import unittest
import valideer
from valideer import ValidationError as error

from tornwrap.validators import *


class Test(unittest.TestCase):
    def test_uuid(self):
        schema = valideer.parse({"value": "uuid"})
        self.assertTrue(schema.validate(dict(value='84fc2f3a-f199-42ba-b24b-fa46455952f4')))
        self.assertRaises(error, schema.validate, dict(value='84fc2f3a-**-42ba-b24b-fa46455952f4'))
        self.assertRaises(error, schema.validate, dict(value='84fc2f3a-42ba-b24b-fa46455952f4'))
        self.assertRaises(error, schema.validate, dict(value=None))

    def test_boolean(self):
        schema = valideer.parse({"value": "bool"})
        for x in ('y', 'yes', '1', 't', 'true', True, 'on'):
            self.assertTrue(schema.validate(dict(value=x))['value'])

        for x in ('n', 'no', '0', 'f', 'false', False, 'off'):
            self.assertFalse(schema.validate(dict(value=x))['value'])

        for x in ('not', None, 'random', object(), int):
            self.assertRaises(error, schema.validate, dict(value=x))
