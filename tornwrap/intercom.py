import os
import valideer
from tornado import gen
from valideer import accepts
from tornado import httpclient
from tornado.web import HTTPError
from tornado.escape import json_decode
from tornado.escape import json_encode
from tornado.httputil import url_concat

from .logger import log

endpoints = valideer.Enum(('users', 'companies', 'admins', 'tags', 
                           'segments', 'notes', 'events', 'counts', 'conversations'))


class Intercom(object):
    """
    http://doc.intercom.io/api/
    """
    def __init__(self, ignore_error=False, api_key=None):
        self.api_key = api_key or os.getenv('INTERCOM_API_KEY', None)
        assert self.api_key, 'intercom api_key must be set'
        self._endpoints = ['https://%s@api.intercom.io/' % self.api_key]
        self._ignore_error = ignore_error

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
        kwargs = dict([(k, v) for k,v in kwargs.items() if v is not None])

        try:
            if method in ('GET', 'DELETE'):
                response = yield http_client.fetch(url_concat("/".join(self._endpoints), kwargs), 
                                                  headers={'Accept':'application/json'},
                                                  method=method)
            else:
                response = yield http_client.fetch("/".join(self._endpoints), 
                                                  headers={'Content-Type':'application/json'},
                                                  method=method,
                                                  body=json_encode(kwargs))

            result = json_decode(response.body)
            raise gen.Return(result)

        except httpclient.HTTPError as e:
            body = json_decode(e.response.body)
            log.error(json_encode(dict(status=e.response.code, body=body, api=e.response.effective_url)))
            if self._ignore_error:
                raise gen.Return(False)
            raise HTTPError(400, reason=body['errors'][0]['message'])
