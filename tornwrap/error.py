from json import dumps
from tornado import template
import traceback as _traceback
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.web import RequestHandler
from valideer.base import get_type_name
from tornado.web import MissingArgumentError

from . import logger

try:
    import rollbar
except ImportError: # pragma: no cover
    rollbar = None




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


class ErrorHandler(RequestHandler):
    def initialize(self, *a, **k):
        super(ErrorHandler, self).initialize(*a, **k)
        if self.settings.get('error_template'):
            assert self.settings.get('template_path'), "settings `template_path` must be set to use custom `error_template`"

    def get_rollbar_payload(self):
        """Override with your implementation of retrieving error payload data
        ex.
          {
            "person": { "id": "10, "name": "joe", "email": "joe@example.com"}
          }
        """
        return {}

    def get_log_payload(self):
        return {}

    def log(self, lvl=None, _exception_title=None, exc_info=None, **kwargs):
        # critical, error, warning, info, debug
        lvl = (lvl or 'info').lower()
        try:
            if exc_info:
                logger.traceback(exc_info=exc_info)

            if lvl in ('critical', 'error') and self.settings.get('rollbar_access_token'):
                try:
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L246
                    self._rollbar_token = rollbar.report_message(_exception_title or "Generic", level=lvl,
                                                                 request=self.request,
                                                                 extra_data=kwargs,
                                                                 payload_data=self.get_rollbar_payload())
                    kwargs['rollbar'] = self._rollbar_token
                except: # pragma: no cover
                    logger.traceback()

            getattr(logger.log, lvl)(dumps(kwargs, default=logger.json_defaults))

        except: # pragma: no cover
            logger.traceback()

    def traceback(self, **kwargs):
        logger.traceback(**kwargs)

    def log_exception(self, typ, value, tb):
        try:
            if typ is MissingArgumentError:
                self.log("warning", "MissingArgumentError", missing=str(value))
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

                self.log('warning', "ValidationError", **details)
                self.write_error(400, type="ValidationError", reason=str(value), details=details, exc_info=(typ, value, tb))

            elif typ is AssertionError:
                self.write_error(400, type="AssertionError", reason=str(value), exc_info=(typ, value, tb))

            else:
                if typ is not HTTPError or (typ is HTTPError and value.status_code >= 500):
                    logger.traceback(exc_info=(typ, value, tb))

                if self.settings.get('rollbar_access_token') and not (typ is HTTPError and value.status_code < 500):
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L218
                    try:
                        self._rollbar_token = rollbar.report_exc_info(exc_info=(typ, value, tb), request=self.request, payload_data=self.get_rollbar_payload())
                    except Exception as e: # pragma: no cover
                        logger.log.error("Rollbar exception: %s", str(e))

                super(ErrorHandler, self).log_exception(typ, value, tb)

        except: # pragma: no cover
            super(ErrorHandler, self).log_exception(typ, value, tb)

    def write_error(self, status_code, type=None, reason=None, details=None, exc_info=None, **kwargs):
        if exc_info:
            traceback = ''.join(["%s<br>" % line for line in _traceback.format_exception(*exc_info)])
        else:
            exc_info = [None, None]
            traceback = None

        rollbar_token = getattr(self, "_rollbar_token", None)
        if rollbar_token:
            self.set_header('X-Rollbar-Token', rollbar_token)
        args = dict(status_code=status_code, 
                    type=type,
                    reason=reason or self._reason or exc_info[1],
                    details=details,
                    rollbar=rollbar_token,
                    traceback=traceback, 
                    request=dumps(self.request.__dict__, indent=2, default=lambda a: str(a)))

        self.set_status(status_code)
        if self.settings.get('error_template'):
            self.render(self.settings.get('error_template'), **args)
        else:
            self.finish(TEMPLATE.generate(**args))

    def get(self, *a, **k):
        raise HTTPError(404)
