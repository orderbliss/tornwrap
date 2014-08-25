import valideer
from tornado.web import Application
from tornado.web import RequestHandler
from tornado.testing import AsyncHTTPTestCase

from tornwrap import validated


class Handler(RequestHandler):
    @validated({"+name":valideer.Enum(("steve", "casey"))})
    def get(self):
        self.finish("Hello, %s!" % self.validated.get('name', 'nobody'))

    @validated({"name":valideer.Enum(("steve", "casey"))})
    def post(self):
        self.finish("Hello, %s!" % self.validated.get('name', 'nobody'))

    @validated({"+name":valideer.Enum(("steve", "casey"))}, urlargs=False)
    def put(self):
        self.finish("Hello, %s!" % self.validated.get('name', 'nobody'))


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
        response = self.fetch("/", method="POST", body="name=steve")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Hello, steve!")

    def test_invali_body_args(self):
        response = self.fetch("/", method="POST", body="name")
        self.assertEqual(response.code, 400)

    def test_valid_accepts(self):
        response = self.fetch("/", method="POST", body="name=steve", headers={"Accept": "application/json"})
        self.assertEqual(response.code, 400)

    def test_extra_params(self):
        response = self.fetch("/?exta=true", method="PUT", body="name=steve")
        self.assertEqual(response.code, 200)

    def test_valid_body_json(self):
        response = self.fetch("/", method="POST", body='{"name": "casey"}')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Hello, casey!")

    def test_invalid(self):
        response = self.fetch("/?name=joe")
        self.assertEqual(response.code, 400)
