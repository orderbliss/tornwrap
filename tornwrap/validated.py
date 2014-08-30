import re
from valideer import parse
from functools import wraps
from urlparse import parse_qs
from tornado.web import HTTPError
from tornado.escape import json_decode

from .validators import *


def validated(arguments=None, body=None, extra_arguments=False, extra_body=False):
    # arguments to ignore parsing
    ignore = re.compile(r"^_")
    application_json = re.compile(r".*application.+json.*")
    body = parse(body, additional_properties=extra_body) if body else None
    arguments = parse(arguments, additional_properties=extra_arguments) if arguments else None

    def wrapper(method):
        @wraps(method)
        def validate(self, *args, **kwargs):
            # ------------------
            # Validate Body Data
            # ------------------
            if body and self.request.body:
                try:
                    _body = json_decode(self.request.body)
                except:
                    print "\033[92m....\033[0m", application_json.match(self.request.headers.get('Accept', '')), self.request.headers.get('Accept', '')
                    if application_json.match(self.request.headers.get('Accept', '')):
                        raise HTTPError(400, "no json object could be decoded")

                    # ex. key1=value2&key2=value2
                    try:
                        _body = dict([(k, v[0] if len(v)==1 else v) for k, v in parse_qs(self.request.body, strict_parsing=True).items()])
                    except:
                        raise HTTPError(400, "body was not able to be decoded")

                kwargs["body"] = body.validate(_body)

            elif body is False and self.request.body:
                raise HTTPError(400, "no body arguments allowed")

            # -------------------
            # Validate URL Params
            # -------------------
            if arguments:
                # include url arguments
                _arguments = dict([(k, v[0] if len(v)==1 else v) for k, v in self.request.query_arguments.items() if v!=[''] and not ignore.match(k)]) \
                             if self.request.query_arguments else {}
                kwargs["arguments"] = arguments.validate(_arguments)

            elif arguments is False:
                if any(map(ignore.match, self.request.arguments)):
                    raise HTTPError(400, "no url arguments allowed")

            return method(self, *args, **kwargs)

        return validate
    return wrapper
