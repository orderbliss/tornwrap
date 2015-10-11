import os
import valideer
from tornado import gen
from valideer import accepts
from tornado import httpclient
from tornado.escape import json_decode
from tornado.escape import json_encode
from tornado.httputil import url_concat

from .logger import log
from .logger import traceback

endpoints = valideer.Enum(('users', 'companies', 'admins', 'tags',
                           'segments', 'notes', 'events', 'counts', 'conversations'))


class Intercom(object):
    """
    http://doc.intercom.io/api/
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('INTERCOM_API_KEY', None)
        assert self.api_key, 'intercom api_key must be set'
        self._endpoints = ['https://%s@api.intercom.io/' % self.api_key]

    @accepts(endpoint=endpoints)
    def __getattr__(self, endpoint):
        self._endpoints.append(endpoint)
        return self

    def __getitem__(self, arg):
        self._endpoints.append(arg)
        return self

    @gen.coroutine
    def get(self, httpclient=None, **kwargs):
        result = yield self._api_request('GET', httpclient, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def post(self, httpclient=None, **kwargs):
        result = yield self._api_request('POST', httpclient, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def delete(self, httpclient=None, **kwargs):
        result = yield self._api_request('DELETE', httpclient, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def put(self, httpclient=None, **kwargs):
        result = yield self._api_request('PUT', httpclient, kwargs)
        raise gen.Return(result)

    @gen.coroutine
    def _api_request(self, method, http_client, kwargs):
        if not http_client:
            http_client = httpclient.AsyncHTTPClient()

        # kwargs = validation.validate(kwargs)
        kwargs = dict([(k, v) for k, v in kwargs.items() if v is not None])
        try:
            try:
                if method in ('GET', 'DELETE'):
                    response = yield http_client.fetch(url_concat("/".join(self._endpoints), kwargs),
                                                       headers={'Accept': 'application/json'},
                                                       method=method)
                else:
                    response = yield http_client.fetch("/".join(self._endpoints),
                                                       headers={'Content-Type': 'application/json'},
                                                       method=method, body=json_encode(kwargs))

                log(service="intercom", status=response.code, stripe=response.body, url=response.effective_url)
                raise gen.Return((response.code, json_decode(response.body)))

            except httpclient.HTTPError as e:
                log(service="intercom", status=e.response.code, body=e.response.body, url=e.response.effective_url)
                raise gen.Return((e.response.code, json_decode(e.response.body)))

        except gen.Return:
            raise

        except Exception as e:
            traceback(service="intercom")
            raise gen.Return((500, {'errors': [{'message': 'unknown', 'code': 'unknown'}], 'type': 'error.list'}))
