import valideer
from tornado.web import Application
from tornado.web import RequestHandler
from tornado.testing import AsyncHTTPTestCase

from tornwrap import validated


class Handler(RequestHandler):
    @validated({"+name": valideer.Enum(("steve", "joe"))})
    def get(self, arguments):
        self.finish("Hello, %s!" % arguments.get('name', 'nobody'))

    @validated(body={"name": valideer.Enum(("steve", "joe"))})
    def post(self, body):
        self.finish("Hello, %s!" % body.get('name', 'nobody'))

    @validated(body=False, arguments=False)
    def patch(self):
        self.finish("Hello, World!")

    @validated(arguments={"joe": "bool"}, body={"+name": valideer.Enum(("steve", "joe"))})
    def put(self, arguments, body):
        self.finish("Hello, %s!" % arguments.get('name', 'nobody'))

    def _handle_request_exception(self, e):
        if isinstance(e, valideer.ValidationError):
            self.set_status(400)
            self._reason = str(e)
            self.write_error(400, reason=str(e))
        else:
            super(Handler, self)._handle_request_exception(e)


class Test(AsyncHTTPTestCase):
    def get_app(self):
        return Application([('/', Handler)])

    def test_missing(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 400)

    def test_valid_urlparams(self):
        response = self.fetch("/?name=steve")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Hello, steve!")

    def test_valid_body_args(self):
        response = self.fetch("/?this=not+checked", method="POST", body="name=steve")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Hello, steve!")

    def test_no_body_args(self):
        self.assertEqual(self.fetch("/?this=no", method="PATCH", body="").code, 400)
        self.assertEqual(self.fetch("/", method="PATCH", body='{"no":0}').code, 400)
        self.assertEqual(self.fetch("/", method="PATCH", body="").code, 200)
        self.assertEqual(self.fetch("/?_=123456789", method="PATCH", body="").code, 200)

    def test_invalid_body_args(self):
        response = self.fetch("/", method="POST", body="name")
        self.assertEqual(response.code, 400)

    def test_ignore_empty(self):
        response = self.fetch("/?joe=", method="POST", body="name=joe")
        self.assertEqual(response.code, 200)

    def test_valid_accepts(self):
        response = self.fetch("/", method="POST", body="name=steve", headers={"Accept": "application/json"})
        self.assertEqual(response.code, 200)

    def test_extra_params(self):
        response = self.fetch("/?joe=true", method="PUT", body="name=steve")
        self.assertEqual(response.code, 200)

    def test_valid_body_json(self):
        response = self.fetch("/", method="POST", body='{"name": "joe"}')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Hello, joe!")

    def test_invalid(self):
        response = self.fetch("/?name=andy")
        self.assertEqual(response.code, 400)

    def test_multiple(self):
        response = self.fetch("/?name=steve&name=andy")
        self.assertEqual(response.code, 400)

    def test_initial_values(self):
        self.assertRaises(ValueError, validated, arguments=True)
        self.assertRaises(ValueError, validated, body=True)
