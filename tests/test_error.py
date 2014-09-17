import os
import rollbar
import valideer
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase

from tornwrap import ErrorHandler
from tornwrap import logger

def tryint(v):
    try:
        return int(v)
    except:
        return v

class Handler(ErrorHandler):
    def get_rollbar_payload(self):
        return dict(person=dict(name="joe"))

    def get_log_payload(self):
        return dict(user=10)

    def get(self, type):
        if type == 'validation':
            dic = dict([(k,tryint(v[0])) for k,v in self.request.arguments.items()])
            valideer.parse(dict(value="string", pattern=valideer.Pattern(r"^match\sthi")), additional_properties=False).validate(dic)
        elif type == 'assert':
            assert True is False, 'never gonna happen'
        elif type == 'arg':
            self.get_argument("required")

    def post(self, arg):
        raise Exception("uncaught")


class NoPayloadHandler(ErrorHandler):
    def get(self):
        self.finish(self.get_rollbar_payload())


class Test(AsyncHTTPTestCase):
    def get_app(self):
        return Application([(r'/no/payload', NoPayloadHandler), (r'/(\w+)', Handler)], log_function=logger.handler)

    def test_no_payload(self):
        response = self.fetch("/no/payload")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "{}")

    def test_basics(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

        response = self.fetch("/apples", method="PUT", body="")
        self.assertEqual(response.code, 405)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

    def test_validation(self):
        response = self.fetch("/validation?value=10")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("<h1>400</h1>", response.body)
        self.assertIn("<pre>Invalid value 10 (int): must be string (at value)</pre>", response.body)

        response = self.fetch("/validation?pattern=fail")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("<h1>400</h1>", response.body)
        self.assertIn("(str): must match pattern ^match", response.body)

    def test_assertion(self):
        response = self.fetch("/assert")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("<h1>400</h1>", response.body)
        self.assertIn("<pre>never gonna happen</pre>", response.body)
        self.assertIn("&quot;uri&quot;: &quot;/assert&quot;,", response.body)

    def test_arg(self):
        response = self.fetch("/arg")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("<h1>400</h1>", response.body)
        self.assertIn("<pre>Missing required argument `required`</pre>", response.body)
        self.assertIn("&quot;uri&quot;: &quot;/arg&quot;,", response.body)


class TestRollbar(AsyncHTTPTestCase):
    def get_app(self):
        rollbar.init(os.getenv('ROLLBAR_TOKEN'), environment='tornwrap-ci')
        return Application([('/(\w+)?', Handler)], 
                           error_template="error.html",
                           template_path="./tests",
                           rollbar_access_token=os.getenv('ROLLBAR_TOKEN'),
                           default_handler_class=ErrorHandler)

    def test_basics(self):
        response = self.fetch("/page/404")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("Your custom error page for 404", response.body)

    def test_details(self):
        response = self.fetch("/validation?extra=t")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

        response = self.fetch("/validation?value=10")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

    def test_rollbar(self):
        response = self.fetch("/", method="POST", body="")
        self.assertEqual(response.code, 500)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertRegexpMatches(response.headers.get('X-Rollbar-Token'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")
        self.assertIn("Your custom error page for 500", response.body)

