from time import time
from tornado import testing
from tornado.web import HTTPError
from tornado.testing import AsyncTestCase

from tornwrap import Intercom


class Test(AsyncTestCase):
    @testing.gen_test
    def test_ok(self):
        users = yield Intercom().users.get()
        self.assertEqual(users['total_count'], 0)

    @testing.gen_test
    def test_error(self):
        try:
            yield Intercom().events.post(email="ci@example.com", event_name="hello-world", created_at=int(time()))
        except HTTPError as e:
            self.assertEqual(e.reason, "User Not Found")
        else:
            self.assertTrue(False)
