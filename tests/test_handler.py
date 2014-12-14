import os
import rollbar
import valideer
from json import loads
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase

from tornwrap import RequestHandler
from tornwrap import logger

def tryint(v):
    try:
        return int(v)
    except:
        return v


class TestContentType(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            def get(self):
                self.finish(dict(hello="world", url=self.get_url()))
        return Application([(r'/', Handler)], log_function=logger.handler)

    def test_json(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')
        body = loads(response.body)
        self.assertEqual(body['meta']['status'], 200)
        self.assertRegexpMatches(response.headers.get('X-Request-Id'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")
        self.assertEqual(body['url'], "http://localhost:%s/"%str(self.get_http_port()))


class TestListResult(AsyncHTTPTestCase):
    def get_app(self):
        class Handler(RequestHandler):
            resource = "data"
            def get(self):
                self.finish(["a", "b"])
        return Application([(r'/', Handler)], log_function=logger.handler)

    def test_json(self):
        response = self.fetch("/")
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

    def test_json(self):
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
        response = self.fetch("/")
        self.assertEqual(response.code, 500)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')
        self.assertEqual(response.headers.get('X-Rollbar-Token'), None)


class Handler(RequestHandler):
    def get(self, type):
        if type == 'validation':
            dic = dict([(k,tryint(v[0])) for k,v in self.request.arguments.items()])
            valideer.parse(dict(value="string", pattern=valideer.Pattern(r"^match\sthi")), additional_properties=False).validate(dic)
        elif type == 'missing_argument':
            self.get_argument("required")
        self.finish(dict(url=self.get_url()))

    def post(self, arg):
        try:
            raise Exception("caught")
        except:
            self.traceback(extra_data="ok")
            
        raise Exception("uncaught")


class TestRollbar(AsyncHTTPTestCase):
    def get_app(self):
        rollbar.init(os.getenv('ROLLBAR_TOKEN'), environment='tornwrap-ci')
        return Application([('/(\w+)?', Handler)], 
                           error_template="error.html",
                           template_path="./tests",
                           rollbar_access_token=os.getenv('ROLLBAR_TOKEN'),
                           default_handler_class=RequestHandler)

    def test_basics(self):
        response = self.fetch("/page/405", headers={"Accept": "text/html"})
        self.assertEqual(response.code, 405)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html')

    def test_details(self):
        response = self.fetch("/validation?extra=t", headers={"Accept": "text/html"})
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html')

        response = self.fetch("/validation?value=10", headers={"Accept": "text/html"})
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html')

        response = self.fetch("/missing_argument")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=UTF-8')

    def test_rollbar(self):
        response = self.fetch("/", method="POST", body="")
        self.assertEqual(response.code, 500)
        self.assertRegexpMatches(response.headers.get('X-Rollbar-Token'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")

