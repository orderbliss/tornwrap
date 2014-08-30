import unittest
import valideer
import timestring
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

    def test_email(self):
        schema = valideer.parse({"email": "email"})
        for email in ('joe@example.com', 'hello@codecov.io', 'some123_!@a.b.cc.com'):
            self.assertEqual(schema.validate(dict(email=email))['email'], email.lower())

        for email in ('needsanat', 'nodom@fefe'):
            self.assertRaises(error, schema.validate, dict(email=email))

    def test_callable(self):
        schema = valideer.parse({"callable": "callable"})

        def callback(): pass

        class _object(object):
            def __call__(self): pass

        for _callable in (callback, _object()):
            self.assertEqual(schema.validate(dict(callable=_callable))['callable'], _callable)

        for _callable in ('needsanat', 1):
            self.assertRaises(error, schema.validate, dict(callable=_callable))

    def test_date(self):
        schema = valideer.parse({"date": "date"})
        for date in ('jan 15th 2015', 'tomorrow at 10:30', 'last tuesday'):
            self.assertEqual(schema.validate(dict(date=date))['date'], timestring.Date(date))

    def test_daterange(self):
        schema = valideer.parse({"daterange": "daterange"})
        for daterange in ('2 weeks', 'this year', 'next thursday'):
            self.assertEqual(schema.validate(dict(daterange=daterange))['daterange'], timestring.Range(daterange))
