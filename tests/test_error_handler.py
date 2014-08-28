import os
import rollbar
from tornado.web import Application
from valideer import ValidationError
from tornado.testing import AsyncHTTPTestCase

from tornwrap import ErrorHandler


class Handler(ErrorHandler):
    def get_payload(self):
        return {"person": {"name": "joe"}}

    def get(self, type):
        if type == 'validation':
            raise ValidationError("ValidationError exception")
        elif type == 'assert':
            assert True is False, 'never gonna happen'
        elif type == 'arg':
            self.get_argument("required")
        else:
            raise Exception("Generic exception")

class OtherHandler(ErrorHandler):
    def prepare(self):
        self.settings['error_template'] = "../tests/error.html"
        self.settings['rollbar_access_token'] = os.getenv('ROLLBAR_TOKEN')
        rollbar.init(self.settings['rollbar_access_token'], environment='tornwrap-ci')

    def post(self):
        assert True is False, 'never gonna happen'


class Test(AsyncHTTPTestCase):
    def get_app(self):
        return Application([('/(\w+)', Handler)])

    def test_basics(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

        response = self.fetch("/apples", method="POST", body="")
        self.assertEqual(response.code, 405)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

    def test_validation(self):
        response = self.fetch("/validation")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertIn("<h1>400</h1>", response.body)
        self.assertIn("<pre>ValidationError exception</pre>", response.body)
        self.assertIn("&quot;uri&quot;: &quot;/validation&quot;,", response.body)

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


class TestAgain(AsyncHTTPTestCase):
    def get_app(self):
        return Application([('/', OtherHandler)])

    def test_basics(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')

    def test_template(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertEqual(response.body, "Your custom error page for 404\n")

    def test_rollbar(self):
        response = self.fetch("/", method="POST", body="")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html; charset=UTF-8')
        self.assertRegexpMatches(response.headers.get('X-Rollbar-Token'), r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")
        self.assertEqual(response.body, "Your custom error page for 400\n")

