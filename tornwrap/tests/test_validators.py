import unittest
import valideer
import timestring
from ddt import ddt, data
from valideer import ValidationError as error

from tornwrap.validators import *


@ddt
class Test(unittest.TestCase):
    def test_commit(self):
        schema = valideer.parse({"value": "commit"})
        for commit in ('d5eb3baabe1149158817640f9e27e6b947aef043',
                       'd5eb3baabe1149158817640f9e27e6b947aef043',
                       '1341:233tmgpeqmgpqm',
                       '2f540b1af5fb5f432be686a77ed5206b589a7b52'):
            assert schema.validate(dict(value=commit))

        self.assertRaises(valideer.ValidationError, schema.validate, dict(value='_something odd'))
        self.assertRaises(valideer.ValidationError, schema.validate, dict(value=None))

    @data(("y", True), ("yes", True), ("1", True), ("t", True), ("true", True), ("on", True), (True, True),
          ("n", False), ("no", False), ("0", False), ("f", False), ("false", False), ("off", False), (False, False),
          ('idk', None), (range(10), None))
    def test_bool(self, (value, boolean)):
        if boolean is None:
            with self.assertRaises(valideer.ValidationError):
                validators.boolean().validate(value)
        else:
            res = validators.boolean().validate(value)
            assert res == boolean

    def test_version(self):
        schema = valideer.parse({"value": "version"})
        for version in ('0.0.1', '0.0.10', '0.2.10', '1.2.1'):
            assert schema.validate(dict(value=version))

        self.assertRaises(valideer.ValidationError, schema.validate, dict(value='-124.12.51'))
        self.assertRaises(valideer.ValidationError, schema.validate, dict(value='_something-odd'))
        self.assertRaises(valideer.ValidationError, schema.validate, dict(value=None))

    def test_handler(self):
        schema = valideer.parse({"value": "handler"})
        for handler in ('valid-handler', 'someothername', '__hello.world-ok'):
            assert schema.validate(dict(value=handler))

        for invalid in "!@#{$%^&*(),<>?/'\";:[]{}\\|~`+":
            self.assertRaises(valideer.ValidationError, schema.validate, dict(value='characters'+invalid))
        self.assertRaises(valideer.ValidationError, schema.validate, dict(value=None))

    def test_file(self):
        schema = valideer.parse({"value": "file"})
        for handler in ('app/base.py', 'codecov.sh'):
            assert schema.validate(dict(value=handler))

        for invalid in ('not/a/path', '**#^@', '../black'):
            self.assertRaises(valideer.ValidationError, schema.validate, dict(value=invalid))

    def test_branch(self):
        schema = valideer.parse({"branch": "branch"})
        for x in ('master', 'stable', 'something/thisoem', '-aples', '.dev', 'builds,/1@#$%&*'):
            assert schema.validate(dict(branch=x))

        for x in (False, None):
            self.assertRaises(valideer.ValidationError, schema.validate, dict(branch=x))

    def test_uuid(self):
        schema = valideer.parse({"value": "uuid"})
        self.assertTrue(schema.validate(dict(value='84fc2f3a-f199-42ba-b24b-fa46455952f4')))
        self.assertRaises(error, schema.validate, dict(value='84fc2f3a-**-42ba-b24b-fa46455952f4'))
        self.assertRaises(error, schema.validate, dict(value='84fc2f3a-42ba-b24b-fa46455952f4'))
        self.assertRaises(error, schema.validate, dict(value=None))

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

    def test_ref(self):
        schema = valideer.parse({"value": "ref"})

        self.assertEqual(schema.validate(dict(value="a"*40))['value'], "a"*40)
        self.assertEqual(schema.validate(dict(value="apples"))['value'], "apples")

        for x in (None, object(), int, -50):
            self.assertRaises(error, schema.validate, dict(value=x))

    def test_email(self):
        schema = valideer.parse({"email": "email"})
        for email in ('def post(self, @example.com', 'hello@codecov.io', 'some123_!@a.b.cc.com'):
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

        def callback():
            pass

        class _object(object):
            def __call__(self):
                pass

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
