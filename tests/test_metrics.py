import redis
import unittest

from tornwrap import metrics

class SomeException(Exception):
    pass

class Test(unittest.TestCase):
    redis = redis.Redis()

    @classmethod
    def setUp(self):
        self.redis.flushall()

    def test_speed(self):
        with metrics.speed('download', redis=self.redis):
            pass
        self.assertGreater(float(self.redis.lpop('download')), 0)

    def test_incr(self):
        with metrics.incr('feature.help', redis=self.redis):
            pass
        self.assertEqual(self.redis.get('feature.help'), '1')

        with self.assertRaises(SomeException):
            with metrics.incr('feature.other', redis=self.redis):
                raise SomeException
        self.assertEqual(self.redis.get('feature.other'), None)

        with self.assertRaises(SomeException):
            with metrics.incr('feature.worked', 'feature.failed', redis=self.redis):
                raise SomeException
        self.assertEqual(self.redis.get('feature.failed'), '1')
        self.assertEqual(self.redis.get('feature.worked'), None)
