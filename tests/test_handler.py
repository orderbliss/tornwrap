import unittest
from json import loads
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase

from tornwrap import logger
from tornwrap import RequestHandler


def tryint(v):
    try:
        return int(v)
    except:
        return v


class TestLogHandler(unittest.TestCase):
    @property
    def request(self):
        return self

    @property
    def method(self):
        return 'GET'

    @property
    def _reason(self):
        return 'Success'

    @property
    def uri(self):
        return '/?access_token=abc123'

    def get_status(self):
        return 200

    def request_time(self):
        return 30

    def test_scrubs_data(self):
        res = logger.handler(self)
        self.assertEqual(res['status'], 200)
        self.assertEqual(res['method'], 'GET')
        self.assertEqual(res['reason'], 'Success')
        self.assertEqual(res['url'], '/?access_token=secret')


class TestContentType(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            def get(self):
                self.finish(dict(hello="world", url=self.get_url()))
        return Application([(r'/', Handler)], log_function=logger.handler)

    def test_json(self):
        response = self.fetch("/", headers={"Accept": "application/json"})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')
        body = loads(response.body)
        self.assertEqual(body['meta']['status'], 200)
        self.assertRegexpMatches(response.headers.get('X-Request-Id'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")
        self.assertEqual(body['url'], "http://localhost:%s/" % str(self.get_http_port()))


class TestListResult(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            resource = "data"

            def get(self):
                self.finish(["a", "b"])
        return Application([(r'/', Handler)], log_function=logger.handler)

    def test_json(self):
        response = self.fetch("/", headers={"Accept": "application/json"})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')
        body = loads(response.body)
        self.assertEqual(body['meta']['status'], 200)
        self.assertEqual(body['data'], ["a", "b"])
        self.assertRegexpMatches(response.headers.get('X-Request-Id'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")


class TestString(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            def get(self):
                self.finish("what")
        return Application([(r'/', Handler)], log_function=logger.handler)

    def test_string(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertEqual(response.body, "what")
        self.assertRegexpMatches(response.headers.get('X-Request-Id'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")


class TestErrorNoRollbar(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            def get(self):
                raise Exception("hello")
        return Application([(r'/', Handler)])

    def test_json(self):
        response = self.fetch("/", headers={"Accept": "application/json"})
        self.assertEqual(response.code, 500)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')
        self.assertEqual(response.headers.get('X-Rollbar-Token'), None)
