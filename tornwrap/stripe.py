import os
import valideer
from tornado import gen
from valideer import accepts
from urllib import urlencode
from tornado import httpclient
from tornado.escape import json_decode
from tornado.escape import json_encode
from tornado.httputil import url_concat

from .logger import log

endpoints = valideer.Enum(('charges', 'customers', 'cards', 
                           'subscription', 'plans', 'coupons', 
                           'discount', 'invoices', 'upcoming', 
                           'lines', 'invoiceitems', 'dispute', 
                           'close', 'transfers', 'cancel',
                           'recipients', 'application_fees', 
                           'refund', 'account', 'balance', 'subscriptions',
                           'history', 'events', 'tokens', 'incoming'))

class Stripe(object):
    """
    https://stripe.com/docs/api
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('STRIPE_API_KEY', None)
        assert self.api_key, 'stripe api_key must be set'
        self._endpoints = ['https://%s:@api.stripe.com/v1' % self.api_key]

    @accepts(endpoint=endpoints)
    def __getattr__(self, endpoint):
        self._endpoints.append(endpoint)
        return self

    def __getitem__(self, arg):
        self._endpoints.append(arg)
        return self

    @gen.coroutine
    def get(self, http_client=None, **kwargs):
        result = yield self._api_request('GET', http_client, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def post(self, http_client=None, **kwargs):
        result = yield self._api_request('POST', http_client, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def delete(self, http_client=None, **kwargs):
        result = yield self._api_request('DELETE', http_client, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def put(self, http_client=None, **kwargs):
        result = yield self._api_request('PUT', http_client, kwargs)
        raise gen.Return(result)
    
    @gen.coroutine
    def _api_request(self, method, http_client, kwargs):
        if not http_client:
            http_client = httpclient.AsyncHTTPClient()

        # kwargs = validation.validate(kwargs)
        kwargs = dict([(k, v) for k,v in kwargs.items() if v is not None])
        try:
            try:
                if method in ('GET', 'DELETE'):
                    response = yield http_client.fetch(url_concat("/".join(self._endpoints), self._nested_dict_to_url(kwargs)), 
                                                       method=method)
                else:
                    response = yield http_client.fetch("/".join(self._endpoints), 
                                                       method=method, body=urlencode(self._nested_dict_to_url(kwargs)))

                log.info(json_encode(dict(service="stripe", status=response.code, stripe=response.body, url=response.effective_url)))
                raise gen.Return((response.code, json_decode(response.body)))

            except httpclient.HTTPError as e:
                log.info(json_encode(dict(service="stripe", status=e.response.code, body=e.response.body, url=e.response.effective_url)))
                raise gen.Return((e.response.code, json_decode(e.response.body)))

        except gen.Return:
            raise

        except Exception as e:
            log.info(json_encode(dict(service="stripe", error=str(e))))
            raise gen.Return((500, None))


    def _nested_dict_to_url(self, d):
        """
        We want post vars of form:
        {'foo': 'bar', 'nested': {'a': 'b', 'c': 'd'}}
        to become (pre url-encoding):
        foo=bar&nested[a]=b&nested[c]=d
        """
        stk = []
        for key, value in d.items():
            if isinstance(value, dict):
                n = {}
                for k, v in value.items():
                    n["%s[%s]" % (key, k)] = v
                stk.extend(self._nested_dict_to_url(n))
            else:
                stk.append((key, value))
        return stk
