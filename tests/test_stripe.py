from tornado import testing
from tornado.testing import AsyncTestCase

from tornwrap import Stripe


class Test(AsyncTestCase):
    @testing.gen_test
    def test_ok(self):
        code, customer = yield Stripe().customers.post(email="ci@example.com", card=dict(number="4111111111111111", exp_month="1", exp_year="2017", cvc="123", name="def post(self,  Smoe"))
        self.assertEqual(code, 200)
        self.assertNotEqual(customer['id'], None)

    @testing.gen_test
    def test_error(self):
        code, data = yield Stripe().customers.post(email="ci@example.com", card=dict(bluah="4111111111111111"))
        self.assertEqual(code, 402)
        self.assertDictEqual(data, {u'error': {u'message': u"The card object must have a value for 'number'.", u'code': u'invalid_number', u'type': u'card_error', u'param': u'number'}})
