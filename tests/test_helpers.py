import unittest
import timestring
from decimal import Decimal
from datetime import datetime
from tornado.escape import json_encode

from tornwrap.helpers import *


class Test(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(json_encode(dict(html='<div>hello</div>')),
                         '{"html": "<div>hello<\/div>"}')

    def test_json_defaults_decimal(self):
        self.assertEqual(json_encode(dict(data=Decimal('1.2'))),
                         '{"data": 1.2}')

    def test_json_defaults_datetime(self):
        now = datetime.now()
        self.assertEqual(json_encode(dict(data=now)),
                         '{"data": "%s"}' % str(now))

    def test_json_defaults_timestring(self):
        now = timestring.Date('now')
        self.assertEqual(json_encode(dict(data=now)),
                         '{"data": "%s"}' % str(now))
