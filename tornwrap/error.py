from json import dumps
from tornado import template
import traceback as _traceback
from tornado.log import app_log
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.web import RequestHandler
from tornado.escape import json_encode
from valideer.base import get_type_name
from tornado.web import MissingArgumentError

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
    def get_payload(self):
        """Override with your implementation of retrieving error payload data
        ex.
          {
            "person": { "id": "10, "name": "joe", "email": "joe@example.com"}
          }
        """
        return {}

    def log(self, _exception_title=None, kwargs={}):
        try:
            if self.settings.get('rollbar_access_token'):
                try:
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L246
                    self._rollbar_token = rollbar.report_message(_exception_title or "Generic", level='info', 
                                                                 request=self.request,
                                                                 extra_data=kwargs,
                                                                 payload_data=self.get_payload())
                    kwargs['rollbar'] = self._rollbar_token
                except Exception as e: # pragma: no cover
                    app_log.error("Rollbar exception: %s", str(e))

            try:
                kwargs['payload'] = self.get_payload()
                app_log.warning(json_encode(kwargs))
            except Exception as e: # pragma: no cover
                app_log.warning(str(e))

        except Exception as e: # pragma: no cover
            app_log.error("Error logging traceback: %s", str(e))

    def log_exception(self, typ, value, tb):
        try:
            if typ is MissingArgumentError:
                self.log("MissingArgumentError", dict(missing=str(value)))
                self.set_status(400)
                self.write_error(400, type="MissingArgumentError",
                                 reason="Missing required argument `%s`"%value.arg_name, 
                                 exc_info=(typ, value, tb))

            elif typ is ValidationError:
                details = dict(context=value.context,
                               reason=str(value),
                               value=str(repr(value.value)),
                               value_type=get_type_name(value.value.__class__))
                if 'additional properties' in value.msg:
                    details['additional'] = value.value
                if 'is not valid' in value.msg:
                    details['invalid'] = value.context

                self.log("ValidationError", details)
                self.set_status(400)
                self.write_error(400, type="ValidationError", 
                                 reason=str(value), details=details, exc_info=(typ, value, tb))

            elif typ is AssertionError:
              details = value if type(value) is dict else dict(reason=str(value))
              self.log("AssertionError", details)
              self.set_status(400)
              self.write_error(400, type="AssertionError", reason=str(value),
                               details=details, exc_info=(typ, value, tb))

            else:
                if self.settings.get('rollbar_access_token') and not (typ is HTTPError and value.status_code < 500):
                    # https://github.com/rollbar/pyrollbar/blob/d79afc8f1df2f7a35035238dc10ba0122e6f6b83/rollbar/__init__.py#L218
                    try:
                        self._rollbar_token = rollbar.report_exc_info(request=self.request, payload_data=self.get_payload())
                    except Exception as e: # pragma: no cover
                        app_log.error("Rollbar exception: %s", str(e))

                super(ErrorHandler, self).log_exception(typ, value, tb)

        except Exception as e: # pragma: no cover
            app_log.error("Error parsing traceback: %s", str(e))
            super(ErrorHandler, self).log_exception(typ, value, tb)

    def write_error(self, status_code, type=None, reason=None, details=None, exc_info=None, **kwargs):
        # IDEA: create a temp location of traceback? ex /traceback/5543
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

        if self.settings.get('error_template'):
            self.render(self.settings.get('error_template'), **args)
        else:
            self.finish(TEMPLATE.generate(**args))

    def get(self, *a, **k):
        raise HTTPError(404)
