import re
import sys
import rollbar
import tornpsql
from json import dumps
from uuid import uuid4
from tornado import web
import traceback as _traceback
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.httputil import url_concat

from . import logger


REMOVE_ACCESS_TOKEN = re.compile(r"access_token\=(\w+)")

CONTENT_TYPES = {
    "html": "text/html",
    "csv":  "text/csv", # coming soon
    "xml":  "application/vnd.ms-excel", # coming soon
    "txt":  "text/plain",
    "xml":  "text/xml", # coming soon
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
        export = (self.path_kwargs.get('export', None) \
                  or ('html'  if 'text/html'                in accept else \
                      'txt'   if 'text/plain'               in accept else \
                      'csv'   if 'text/csv'                 in accept else \
                      'xml'   if 'text/xml'                 in accept else \
                      'xls'   if 'application/vnd.ms-excel' in accept else \
                      'json'  if 'application/json'         in accept else \
                      self.application.settings.get('export_defaults', {"GET":"html"}).get(self.request.method, 'json'))).replace('.', '')
        self.set_header('Content-Type', "%s; charset=UTF-8" % CONTENT_TYPES[export])
        return export

    def get_rollbar_payload(self):
        return dict(user=self.current_user if hasattr(self, 'current_user') else None, 
                    id=self.id)

    def get_log_payload(self):
        return dict(user=self.current_user if hasattr(self, 'current_user') else None, 
                    id=self.id)

    def get_url(self, *url, **kwargs):
        if url and url[0] is True:
            _url = self.request.path
            defs = self.query.copy()
            defs.update(kwargs)
            kwargs = defs
        else:
            _url = "/".join(url)
        return url_concat("%s://%s/%s" % (self.request.protocol, self.request.host, _url[1:] if _url.startswith('/') else _url), kwargs)

    @property
    def id(self):
        if not hasattr(self, '_id'):
            self._id = self.request.headers.get('X-Request-Id', str(uuid4()))
        return self._id

    def set_default_headers(self):
        del self._headers["Server"]
        self._headers['X-Request-Id'] = self.id

    def log(self, _exception_title=None, exc_info=None, **kwargs):
        try:
            logger.log(kwargs)
        except: # pragma: no cover
            logger.traceback()

    def traceback(self, **kwargs):
        self.save_traceback(sys.exc_info())
        if self.settings.get('rollbar_access_token'):
            try:
                # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L246
                self._rollbar_token = rollbar.report_exc_info(extra_data=kwargs, payload_data=self.get_rollbar_payload())
                kwargs['rollbar'] = self._rollbar_token
            except: # pragma: no cover
                logger.traceback()
        logger.traceback(**kwargs)

    def save_traceback(self, exc_info):
        if not hasattr(self, 'tracebacks'):
            self.tracebacks = []
        self.tracebacks.append(_traceback.format_exception(*exc_info))

    def log_exception(self, typ, value, tb):
        try:
            if typ is web.MissingArgumentError:
                self.log("MissingArgumentError", missing=str(value))
                self.write_error(400, type="MissingArgumentError", reason="Missing required argument `%s`"%value.arg_name, exc_info=(typ, value, tb))

            elif typ is ValidationError:
                self.log("ValidationError", message=str(value))
                self.write_error(400, type="ValidationError", reason=str(value), exc_info=(typ, value, tb))

            else:
                if typ is not HTTPError or (typ is HTTPError and value.status_code >= 500):
                    logger.traceback(exc_info=(typ, value, tb))

                if self.settings.get('rollbar_access_token') and not (typ is HTTPError and value.status_code < 500):
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L218
                    try:
                        self._rollbar_token = rollbar.report_exc_info(exc_info=(typ, value, tb), 
                                                                      request=self.request, 
                                                                      payload_data=self.get_rollbar_payload())
                    except: # pragma: no cover
                        logger.traceback()

                super(RequestHandler, self).log_exception(typ, value, tb)

        except: # pragma: no cover
            super(RequestHandler, self).log_exception(typ, value, tb)


    def finish(self, chunk=None):
        # Manage Results
        # --------------
        if type(chunk) is list:
            chunk = {self.resource:chunk,"meta":{"total":len(chunk)}}

        if type(chunk) is dict:
            chunk.setdefault('meta', {}).setdefault("status", self.get_status() or 200)
            self.set_status(int(chunk['meta']['status']))
            chunk['meta']['request'] = self.id

            export = self.export
            if export in ('txt', 'html'):
                if self.get_status() in (200, 201):
                    # ex:  html/customers_get_one.html
                    doc = "%s/%s_%s_%s.%s" % (export, self.resource, self.request.method.lower(), 
                                              ("one" if self.path_kwargs.get('id') and self.path_kwargs.get('more') is None else "many"), export)
                else:
                    # ex:  html/error/401.html
                    doc = "%s/errors/%s.%s" % (export, self.get_status(), export)

                try:
                    chunk = self.render_string(doc, **chunk)
                except IOError:
                    chunk = "template not found at %s"%doc

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

        self.finish({"error":data})
