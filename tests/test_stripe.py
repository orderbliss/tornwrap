from tornado import testing
from tornado.web import HTTPError
from tornado.testing import AsyncTestCase

from tornwrap import Stripe


class Test(AsyncTestCase):
    @testing.gen_test
    def test_ok(self):
        customer = yield Stripe().customers.post(email="ci@example.com", card=dict(number="4111111111111111", exp_month="1", exp_year="2017", cvc="123", name="Joe Smoe"))
        self.assertNotEqual(customer['id'], None)

    @testing.gen_test
    def test_error(self):
        try:
            yield Stripe().customers.post(email="ci@example.com", card=dict(bluah="4111111111111111"))
        except HTTPError as e:
            self.assertEqual(e.reason, "The card object must have a value for 'number'.")
        else:
            self.assertTrue(False)
