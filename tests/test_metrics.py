import unittest
from time import sleep

from tornwrap import metrics


class SomeException(Exception):
    pass

class Test(unittest.TestCase):
    def test_speed(self):
        with self.assertRaises(SomeException):
            with metrics.new('download') as m:
                sleep(.1)
                m.speed.time('hello')
                m.count.incr("success")
                m.count.incr("fail", 2)
                m.speed.time('again')
                raise SomeException

        self.assertTrue(m.speed.hello>0)
        self.assertTrue(m.speed.hello>0)
        self.assertEqual(m.count.success, 1)
        self.assertEqual(m.count.fail, 2)
