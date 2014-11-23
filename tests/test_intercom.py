from time import time
from tornado import testing
from tornado.testing import AsyncTestCase

from tornwrap import Intercom


class Test(AsyncTestCase):
    @testing.gen_test
    def test_ok(self):
        code, users = yield Intercom().users.get()
        self.assertEqual(code, 200)
        self.assertEqual(users['total_count'], 0)

    @testing.gen_test
    def test_error(self):
        code, data = yield Intercom().events.post(email="ci@example.com", event_name="hello-world", created_at=int(time()))
        self.assertEqual(code, 404)
        data.pop("request_id")
        self.assertDictEqual(data, {u'errors': [{u'message': u'User Not Found', u'code': u'not_found'}], u'type': u'error.list'})
