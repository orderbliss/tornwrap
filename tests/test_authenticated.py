from tornado.web import Application
from tornado.web import RequestHandler
from tornado.testing import AsyncHTTPTestCase

from tornwrap import authenticated


class Handler(RequestHandler):
    def get_authenticated_user(self, user, password):
        if user == "joe" and password == "smoe":
            return dict(name="joe")
        return None

    @authenticated
    def get(self):
        self.write("Hello, world!")


class Test(AsyncHTTPTestCase):
    def get_app(self):
        return Application([('/', Handler)])

    def test_auth_requested(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 401)
        self.assertEqual(response.headers.get('WWW-Authenticate'), 'Basic realm=Restricted')

    def test_is_auth(self):
        response = self.fetch("/", auth_username="joe", auth_password="smoe")
        self.assertEqual(response.code, 200)
        self.assertNotIn('WWW-Authenticate', response.headers)

    def test_is_not_auth(self):
        response = self.fetch("/", auth_username="joe", auth_password="x")
        self.assertEqual(response.code, 401)
        self.assertNotIn('WWW-Authenticate', response.headers)
