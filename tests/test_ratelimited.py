import time
import redis
from tornado.web import Application
from tornado.web import RequestHandler
from tornado.testing import AsyncHTTPTestCase

from tornwrap import ratelimited


class Handler(RequestHandler):
    def initialize(self, redis):
        self.redis = redis

    @ratelimited(guest=(5, 2))
    def get(self):
        self.write("Hello, world!")

    @ratelimited(guest=(1, 2))
    def post(self):
        self.write("Hello, world!")

    @ratelimited(user=(8, 2), guest=(1, 2))
    def put(self):
        self.write("Hello, world!")

    def get_current_user(self):
        return self.request.headers.get('X-User')=='yes'

    def was_rate_limited(self, tokens, remaining, ttl):
        # notice we do not raise HTTPError here
        # because it will reset headers
        self.set_status(403)
        self.finish("Rate Limited")


class TestRateLimit(AsyncHTTPTestCase):
    def get_app(self):
        return Application([('/', Handler, dict(redis=redis.Redis()))])

    def setUp(self):
        redis.Redis().flushall()
        super(TestRateLimit, self).setUp()

    def test_ratelimit_1(self):
        self.ratelimit(5, method="GET")

    def test_ratelimit_2(self):
        self.ratelimit(1, False, method="POST", body="")

    def test_ratelimit_3(self):
        self.ratelimit(8, method="PUT", headers={"X-User": "yes"}, body="")

    def test_ratelimit_4(self):
        self.ratelimit(1, method="PUT", body="")

    def ratelimit(self, tokens, caught=True, **kwargs):
        for again in (1, 1, 0):
            for x in xrange(1, 10):
                remaining = (tokens - x)
                response = self.fetch("/", **kwargs)
                print "Request #", x, response.headers.get("X-RateLimit-Remaining")
                if caught:
                    self.assertEqual(response.headers.get("X-RateLimit-Limit"), str(tokens))
                    self.assertEqual(response.headers.get("X-RateLimit-Remaining"), str(remaining if remaining > 0 else 0))
                    self.assertGreater(response.headers.get("X-RateLimit-Reset"), int(time.mktime(time.localtime())))
                if remaining >= 0:
                    self.assertEqual(response.code, 200)
                    self.assertEqual(response.body, "Hello, world!")
                else:
                    self.assertEqual(response.code, 403)
                    # self.assertEqual(response.body, "Rate Limited")

            # sleep and try again
            if again: time.sleep(2)
