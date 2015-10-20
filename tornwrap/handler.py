import sys
from uuid import uuid4
from tornado import web
from tornado import httpclient
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


CONTENT_TYPES = {
    "html": "text/html",
    "csv":  "text/csv",
    "txt":  "text/plain",
    "xml":  "text/xml",
    "json": "application/json",
}


class RequestHandler(web.RequestHandler):
    export = None

    def initialize(self, *a, **k):
        super(RequestHandler, self).initialize(*a, **k)
        if self.settings.get('error_template'):
            assert self.settings.get('template_path'), "settings `template_path` must be set to use custom `error_template`"

    @property
    def debug(self):
        return self.application.settings.get('debug', False)

    def get_export(self):
        if self.export:
            return self.export
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
        return {}

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

    def log(self, **kwargs):
        try:
            default = self.get_log_payload() or {}
            default['id'] = self.request_id
            default.update(kwargs)
            logger.log(**default)
        except:  # pragma: no cover
            logger.traceback(**kwargs)

    def traceback(self, exc_info=None, **kwargs):
        if not exc_info:
            exc_info = sys.exc_info()
        self.save_traceback(exc_info)
        default = self.get_log_payload() or {}
        default['id'] = self.request_id
        default.update(kwargs)
        logger.traceback(exc_info, **default)

    def save_traceback(self, exc_info):
        if self.settings.get('save_traceback') is True:
            if not hasattr(self, 'tracebacks'):
                self.tracebacks = []
            self.tracebacks.append(_traceback.format_exception(*exc_info))

    def log_exception(self, typ, value, tb):
        if self.debug:
            try:
                from pygments import highlight
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import TerminalFormatter

                tbtext = ''.join(_traceback.format_exception(typ, value, tb))
                lexer = get_lexer_by_name("pytb", stripall=True)
                formatter = TerminalFormatter()
                sys.stderr.write('\n'+highlight(tbtext, lexer, formatter)+'\n')

            except:
                _traceback.print_tb(tb)

        try:
            if typ in (
                web.MissingArgumentError,
                ValidationError,
                AssertionError,
                httpclient.HTTPError,
                HTTPError
            ):
                self._log_error = dict(error=typ.__name__, reason=str(value))

            else:
                self.traceback()

        except:  # pragma: no cover
            super(RequestHandler, self).log_exception(typ, value, tb)

    def write_error(self, status_code, reason=None, exc_info=None):
        error, context = None, None
        if exc_info:
            self.save_traceback(exc_info)

            error = exc_info[1]
            if isinstance(error, ValidationError):
                self.set_status(400)
                if error.context:
                    context = error.context[0] if type(error.context) is list else error.context
                    reason = context + ' ' + str(error.msg)
                else:
                    reason = str(error.msg)

            elif isinstance(error, web.MissingArgumentError):
                self.set_status(400)
                reason = "Missing required argument `%s`" % error.arg_name
                context = error.arg_name

            elif isinstance(error, HTTPError):
                reason = error.reason

            elif isinstance(error, httpclient.HTTPError):
                reason = error.message

            elif isinstance(error, AssertionError):
                self.set_status(400)
                reason = str(error)

            else:
                reason = str(error)

        self.set_status(status_code)
        self.finish({"error": {"reason": reason,
                               "type": type(error).__name__ if error else None,
                               "context": context}})

    def finish(self, chunk=None):
        # Manage Results
        # --------------
        if type(chunk) is list:
            chunk = {self.resource: chunk, "meta": {"total": len(chunk)}}

        if type(chunk) is dict:
            chunk.setdefault('meta', {}).setdefault("status", self.get_status() or 200)
            self.set_status(int(chunk['meta']['status']))
            chunk['meta']['request'] = self.request_id

            export = self.get_export()
            if export in ('txt', 'html'):
                doc = None
                if self.get_status() in (200, 201):
                    if hasattr(self, "resource"):
                        # ex:  html/customers/get_one.html
                        doc = "%s/%s/%s_%s.%s" % (export, self.resource, self.request.method.lower(),
                                                  ("one" if self.path_kwargs.get('id') and self.path_kwargs.get('more') is None else "many"), export)
                else:
                    # ex:  html/error/401.html
                    doc = "%s/errors/%s.%s" % (export, self.get_status(), export)

                if doc:
                    try:
                        chunk = self.render_string(doc, **chunk)
                    except:
                        self.traceback()
                        # no template found
                        if export == 'txt':
                            chunk = "HTTP %s\n%s" % (chunk['meta']['status'], chunk.get('error', {}).get('reason'))

        # Finish Request
        # --------------
        super(RequestHandler, self).finish(chunk)
        return chunk
