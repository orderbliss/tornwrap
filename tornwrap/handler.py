import re
import tornpsql
from json import dumps
from uuid import uuid4
from tornado import web
from tornado import template
import traceback as _traceback
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.httputil import url_concat
from valideer.base import get_type_name

from . import logger
from .helpers import json_defaults

try:
    import rollbar
except ImportError: # pragma: no cover
    rollbar = None


REMOVE_ACCESS_TOKEN = re.compile(r"access_token\=(\w+)")


TEMPLATE = template.Template("""
<html>
<title>Error</title>
<head>
  <link type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.0/styles/github.min.css" rel="stylesheet">
  <style type="text/css">
    body, html{padding: 20px;margin: 20px;}
    h1{font-family: sans-serif; font-size:100px; color:#ececec; text-align:center;}
    h2{font-family: monospace;}
    pre{overflow:scroll; padding: 2em !important;}
  </style>
</head>
<body>
  <h1>{{status_code}}</h1>
  {% if rollbar %}
    <h3><a href="https://rollbar.com/item/uuid/?uuid={{rollbar}}"><img src="https://avatars1.githubusercontent.com/u/3219584?v=2&s=30"> View on Rollbar</a></h3>
  {% end %}
  <h2>Error</h2>
  <pre>{{reason}}</pre>
  <h2>Traceback</h2>
  <pre>{{traceback}}</pre>
  <h2>Request</h2>
  <pre class="json">{{request}}</pre>
</body>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.0/highlight.min.js"></script>
<script type="text/javascript">
  $(function() {
    $('pre').each(function(i, block) {
        hljs.highlightBlock(block);
    });
  });
</script>
</html>
""")


class RequestHandler(web.RequestHandler):
    def initialize(self, *a, **k):
        super(RequestHandler, self).initialize(*a, **k)
        if self.settings.get('error_template'):
            assert self.settings.get('template_path'), "settings `template_path` must be set to use custom `error_template`"

    @property
    def debug(self):
        return self.application.settings['debug']

    @property
    def export(self):
        return (self.path_kwargs.get('export', None) or ('html' if 'text/html' in self.request.headers.get("Accept", "") else 'json')).replace('.', '')

    def get_rollbar_payload(self):
        return dict(user=self.current_user if hasattr(self, 'current_user') else None, id=self.id)

    def get_log_payload(self):
        return dict(user=self.current_user if hasattr(self, 'current_user') else None, id=self.id)

    def get_url(self, *url, **kwargs):
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
        if self.settings.get('rollbar_access_token'):
            try:
                # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L246
                self._rollbar_token = rollbar.report_exc_info(extra_data=kwargs, payload_data=self.get_rollbar_payload())
                kwargs['rollbar'] = self._rollbar_token
            except: # pragma: no cover
                logger.traceback()
        logger.traceback(**kwargs)

    def save_request(self, title, request, response, parsed=None):
        if not hasattr(self, 'apis'):
            self.apis = []
        self.apis.append(dict(request=request, title=title, url=response.effective_url,
                              method=response.request.method,
                              response=dict(body=response.body, 
                                            parsed=parsed, 
                                            status=response.code, 
                                            headers=response.headers)))


    def log_exception(self, typ, value, tb):
        try:
            if typ is web.MissingArgumentError:
                self.log("MissingArgumentError", missing=str(value))
                self.write_error(400, type="MissingArgumentError", reason="Missing required argument `%s`"%value.arg_name, exc_info=(typ, value, tb))

            elif typ is ValidationError:
                details = dict(context=value.context,
                               reason=str(value),
                               value=str(repr(value.value)),
                               value_type=get_type_name(value.value.__class__))
                if 'additional properties' in value.msg:
                    details['additional'] = value.value
                if 'is not valid' in value.msg:
                    details['invalid'] = value.context

                self.log("ValidationError", **details)
                self.write_error(400, type="ValidationError", reason=str(value), details=details, exc_info=(typ, value, tb))

            elif typ is AssertionError:
                # you can do: assert False, (404, "not found")
                status, message = (value.message if type(value.message) is tuple else (400, value.message))
                self.write_error(status, type="AssertionError", reason=str(message), exc_info=(typ, message, tb))

            else:
                if typ is not HTTPError or (typ is HTTPError and value.status_code >= 500):
                    logger.traceback(exc_info=(typ, value, tb))

                if self.settings.get('rollbar_access_token') and not (typ is HTTPError and value.status_code < 500):
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L218
                    try:
                        self._rollbar_token = rollbar.report_exc_info(exc_info=(typ, value, tb), request=self.request, payload_data=self.get_rollbar_payload())
                    except Exception as e: # pragma: no cover
                        logger.log.error("Rollbar exception: %s", str(e))

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

            export = self.export
            if export in ('txt', 'html'):
                self.set_header('Content-Type', 'text/%s' % ('plain' if export == 'txt' else 'html'))
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

        # Save Requests
        # -------------
        if self.settings.get('save_requests') is True and self.request.method != "GET" and self.get_status() != 401:
            chunk['meta']['request'] = self.id
            try:
                # ... keep self.error
                #     which may incldue traceback.format_exception(*kwargs["exc_info"])

                # dont save Auth token
                self.request.headers.pop('Authorization', '') 
                # remove ?access_token=abc
                url = REMOVE_ACCESS_TOKEN.sub('access_token=<token>', self.request.uri)
                
                self.db.get("""INSERT INTO requests (requestid, status, endpoint, method, uri, request, api, response, rollbar) 
                               values (%s, %s, %s, %s, %s, %s::json, %s::json, %s::json, %s);""",
                            self.id, str(self.get_status()), self.resource,
                            self.request.method.upper(), url,
                            dumps(dict(headers=self.request.headers, query=self.query, body=self.body), default=json_defaults),
                            dumps(getattr(self, 'apis', None), default=json_defaults),
                            dumps(dict(headers=self._headers, body=chunk), default=json_defaults),
                            self._rollbar_token)
            except:
                self.traceback()

        # Finish Request
        # --------------
        super(RequestHandler, self).finish(chunk)

    def render_string(self, template, **kwargs):
        data = dict(owner=None, repo=None, file_name=None)
        data.update(self.application.extra)
        data.update(self.path_kwargs)
        data.update(kwargs)
        data['debug'] = self.debug
        return super(RequestHandler, self).render_string(template, dumps=dumps, **data)

    # def write_error(self, status_code, type=None, reason=None, details=None, exc_info=None, **kwargs):
    #     if exc_info:
    #         traceback = ''.join(["%s<br>" % line for line in _traceback.format_exception(*exc_info)])
    #     else:
    #         exc_info = [None, None]
    #         traceback = None

    #     rollbar_token = getattr(self, "_rollbar_token", None)
    #     if rollbar_token:
    #         self.set_header('X-Rollbar-Token', rollbar_token)
    #     args = dict(status_code=status_code, 
    #                 type=type,
    #                 reason=reason or self._reason or exc_info[1],
    #                 details=details,
    #                 rollbar=rollbar_token,
    #                 traceback=traceback, 
    #                 request=dumps(self.request.__dict__, indent=2, default=lambda a: str(a)))

    #     self.set_status(status_code)
    #     if self.settings.get('error_template'):
    #         self.render(self.settings.get('error_template'), **args)
    #     else:
    #         self.finish(TEMPLATE.generate(**args))

    def write_error(self, status_code, reason=None, exc_info=None):
        data = dict(for_human=reason or self._reason or "unknown", for_robot="unknown")
        if exc_info:
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
        
        if self._rollbar_token:
            self.set_header('X-Rollbar-Token', self._rollbar_token)
            data['rollbar'] = self._rollbar_token

        self.finish({"error":data})

    def get(self, *a, **k):
        raise HTTPError(404)

