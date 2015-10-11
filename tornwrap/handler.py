import re
import sys
import tornpsql
from json import dumps
from uuid import uuid4
from tornado import web
import traceback as _traceback
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.httputil import url_concat
from tornado.httpclient import AsyncHTTPClient
try:
    import rollbar
except ImportError:
    rollbar = None

from . import logger


REMOVE_ACCESS_TOKEN = re.compile(r"access_token\=(\w+)")

CONTENT_TYPES = {
    "html": "text/html",
    "csv":  "text/csv",
    "txt":  "text/plain",
    "xml":  "text/xml",
    "json": "application/json",
}


class RequestHandler(web.RequestHandler):
    def initialize(self, *a, **k):
        super(RequestHandler, self).initialize(*a, **k)
        if self.settings.get('error_template'):
            assert self.settings.get('template_path'), "settings `template_path` must be set to use custom `error_template`"

    @property
    def debug(self):
        return self.application.settings.get('debug', False)

    @property
    def export(self):
        accept = self.request.headers.get("Accept", "")
        export = (self.path_kwargs.get('export', None)
                  or ('html' if 'text/html' in accept else
                      'json' if 'application/json' in accept else
                      'txt' if 'text/plain' in accept else
                      'csv' if 'text/csv' in accept else
                      'xml' if 'text/xml' in accept else
                      self.application.settings.get('export_defaults', {"GET": "html"}).get(self.request.method, 'json'))).replace('.', '')
        self.set_header('Content-Type', "%s; charset=UTF-8" % CONTENT_TYPES[export])
        return export

    @property
    def query(self):
        if not hasattr(self, "_query"):
            query = dict([(k, v[0] if len(v) == 1 else v) for k, v in self.request.query_arguments.items() if v != ['']]) if self.request.query_arguments else {}
            query.pop('access_token', False)
            query.pop('_', None)  # ?_=1417978116609
            self._query = query
        return self._query

    def was_rate_limited(self, tokens, remaining, ttl):
        raise HTTPError(403, reason="You have been rate limited.")

    @property
    def fetch(self):
        """Quicker method to access
        res = yield self.fetch("...")
        """
        return AsyncHTTPClient().fetch

    def get_log_payload(self):
        return {"request": self.request_id}

    def get_url(self, *url, **kwargs):
        """Create urls quickly using the current requests domain
        """
        if url and url[0] is True:
            _url = self.request.path
            defs = self.query.copy()
            defs.update(kwargs)
            kwargs = defs
        else:
            _url = "/".join(url)
        kwargs = dict([(k, v) for k, v in kwargs.iteritems() if v is not None])
        return url_concat("%s://%s/%s" % (self.request.protocol, self.request.host, _url[1:] if _url.startswith('/') else _url), kwargs)

    @property
    def request_id(self):
        """Access request id value
        """
        if not hasattr(self, '_id'):
            self._id = self.request.headers.get('X-Request-Id', str(uuid4()))
        return self._id

    def set_default_headers(self):
        # set the internal request id in the headers
        self._headers['X-Request-Id'] = self.request_id

    def log(self, _exception_title=None, exc_info=None, **kwargs):
        try:
            default = self.get_log_payload() or {}
            default['request'] = self.request_id
            default.update(kwargs)
            logger.log(default)
        except:  # pragma: no cover
            logger.traceback()

    def traceback(self, **kwargs):
        self.save_traceback(sys.exc_info())
        logger.traceback(**kwargs)

    def save_traceback(self, exc_info):
        if not hasattr(self, 'tracebacks'):
            self.tracebacks = []
        self.tracebacks.append(_traceback.format_exception(*exc_info))

    def log_exception(self, typ, value, tb):
        try:
            if typ is web.MissingArgumentError:
                self.log("MissingArgumentError", missing=str(value))
                self.write_error(400, type="MissingArgumentError", reason="Missing required argument `%s`" % value.arg_name, exc_info=(typ, value, tb))

            elif typ is ValidationError:
                self.log("ValidationError", message=str(value))
                self.write_error(400, type="ValidationError", reason=str(value), exc_info=(typ, value, tb))

            else:
                if typ is not HTTPError or (typ is HTTPError and value.status_code >= 500):
                    logger.traceback(exc_info=(typ, value, tb))

                super(RequestHandler, self).log_exception(typ, value, tb)

        except:  # pragma: no cover
            super(RequestHandler, self).log_exception(typ, value, tb)

    def finish(self, chunk=None):
        # Manage Results
        # --------------
        if type(chunk) is list:
            chunk = {self.resource: chunk, "meta": {"total": len(chunk)}}

        if type(chunk) is dict:
            chunk.setdefault('meta', {}).setdefault("status", self.get_status() or 200)
            self.set_status(int(chunk['meta']['status']))
            chunk['meta']['request'] = self.request_id

            export = self.export
            if export in ('txt', 'html'):
                doc = None
                if self.get_status() in (200, 201):
                    print "\033[92m....\033[0m", 'here'
                    if hasattr(self, "resource"):
                        # ex:  html/customers_get_one.html
                        doc = "%s/%s_%s_%s.%s" % (export, self.resource, self.request.method.lower(),
                                                  ("one" if self.path_kwargs.get('id') and self.path_kwargs.get('more') is None else "many"), export)
                else:
                    # ex:  html/error/401.html
                    doc = "%s/errors/%s.%s" % (export, self.get_status(), export)

                if doc:
                    try:
                        chunk = self.render_string(doc, **chunk)
                    except IOError:
                        chunk = "template not found at " + doc

        # Finish Request
        # --------------
        super(RequestHandler, self).finish(chunk)
        return chunk

    def render_string(self, template, **kwargs):
        data = dict(owner=None, repo=None, file_name=None)
        data.update(getattr(self.application, 'extra', {}))
        data.update(self.path_kwargs)
        data.update(kwargs)
        data['debug'] = self.debug
        return super(RequestHandler, self).render_string(template, dumps=dumps, **data)

    def write_error(self, status_code, reason=None, exc_info=None):
        data = dict(for_human=reason or self._reason or "unknown",
                    for_robot="unknown")
        if exc_info:
            # to the request
            self.save_traceback(exc_info)

            error = exc_info[1]
            if isinstance(error, ValidationError):
                status_code = 400
                data['for_human'] = "Please review the following fields: %s" % ", ".join(error.context)
                data['context'] = error.context
                data['for_robot'] = error.message

            elif isinstance(error, tornpsql.DataError):
                self.error = dict(sql=str(error))
                data['for_robot'] = "rejected sql query"

            elif isinstance(error, HTTPError):
                if error.status_code == 401:
                    self.set_header('WWW-Authenticate', 'Basic realm=Restricted')

                data['for_robot'] = error.log_message

            else:
                data['for_robot'] = str(error)

        self.set_status(status_code)

        if hasattr(self, '_rollbar_token') and self._rollbar_token:
            self.set_header('X-Rollbar-Token', self._rollbar_token)
            data['rollbar'] = self._rollbar_token

        self.finish({"error": data})
