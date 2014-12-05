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

    def test_timezone(self):
        schema = valideer.parse({"value": "timezone"})

        for key, value in timezone.timezones.items():
            self.assertEqual(schema.validate(dict(value=key))['value'], value)

        for x in ('not', None, 'random', object(), int):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_id(self):
        schema = valideer.parse({"value": "id"})

        self.assertEqual(schema.validate(dict(value=1))['value'], 1)
        self.assertEqual(schema.validate(dict(value="50"))['value'], 50)

        for x in ('not', None, 'random', object(), int, -50, "19.123"):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_float(self):
        schema = valideer.parse({"value": "float"})

        self.assertEqual(schema.validate(dict(value=1))['value'], 1)
        self.assertEqual(schema.validate(dict(value="1k"))['value'], 1000)
        self.assertEqual(schema.validate(dict(value="-50"))['value'], -50)
        self.assertEqual(schema.validate(dict(value="5.2k"))['value'], 5200)
        self.assertEqual(schema.validate(dict(value="19.123"))['value'], 19.123)
        self.assertEqual(schema.validate(dict(value=12.91))['value'], 12.91)

        for x in ('not', None, 'random', object(), int, ):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_int(self):
        schema = valideer.parse({"value": "int"})

        self.assertEqual(schema.validate(dict(value=1))['value'], 1)
        self.assertEqual(schema.validate(dict(value="1k"))['value'], 1000)
        self.assertEqual(schema.validate(dict(value="-50"))['value'], -50)
        self.assertEqual(schema.validate(dict(value="5.2k"))['value'], 5200)
        self.assertEqual(schema.validate(dict(value="19.123"))['value'], 19)
        self.assertEqual(schema.validate(dict(value=12.91))['value'], 12)

        for x in ('not', None, 'random', object(), int, ):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_commit(self):
        schema = valideer.parse({"value": "commit"})

        self.assertEqual(schema.validate(dict(value="a"*40))['value'], "a"*40)

        for x in ('not', None, 'random', object(), int, -50, "19.123"):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_ref(self):
        schema = valideer.parse({"value": "ref"})

        self.assertEqual(schema.validate(dict(value="a"*40))['value'], "a"*40)
        self.assertEqual(schema.validate(dict(value="apples"))['value'], "apples")

        for x in (None, object(), int, -50):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_branch(self):
        schema = valideer.parse({"value": "branch"})

        self.assertEqual(schema.validate(dict(value="large-name-that-seems-not-really/cool"))['value'], "large-name-that-seems-not-really/cool")
        self.assertEqual(schema.validate(dict(value="apples"))['value'], "apples")

        for x in (None, object(), int, -50):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_email(self):
        schema = valideer.parse({"email": "email"})
        for email in ('joe@example.com', 'hello@codecov.io', 'some123_!@a.b.cc.com'):
            self.assertEqual(schema.validate(dict(email=email))['email'], email.lower())

        for email in ('needsanat', 'nodom@fefe'):
            self.assertRaises(error, schema.validate, dict(email=email))

    def test_day(self):
        schema = valideer.parse({"day": "day"})
        for (d, v) in ((0, "sun"), (1, "mon"), (2, "tue"), (3, "wed"), (4, "thu"), (5, "fri"), (6, "sat")):
            self.assertEqual(schema.validate(dict(day=d))['day'], d)
            self.assertEqual(schema.validate(dict(day=v))['day'], d)

        for day in ('needsanat', 'nodom'):
            self.assertRaises(error, schema.validate, dict(day=day))

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
        self.assertRaises(error, schema.validate, dict(date="never"))

    def test_daterange(self):
        schema = valideer.parse({"daterange": "daterange"})
        for daterange in ('2 weeks', 'this year', 'next thursday'):
            self.assertEqual(schema.validate(dict(daterange=daterange))['daterange'], timestring.Range(daterange))
        self.assertRaises(error, schema.validate, dict(daterange="never"))
