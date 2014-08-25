from valideer import parse
from functools import wraps
from urlparse import parse_qs
from tornado.web import HTTPError
from tornado.escape import json_decode


def validated(schema, urlargs=True, additional_properties=False):
    parsed = parse(schema, additional_properties=additional_properties)
    def wrapper(method):
        @wraps(method)
        def validate(self, *args, **kwargs):
            body = self.request.body or {}
            if body:
                try:
                    body = json_decode(body)
                except:
                    if 'application/json' in self.request.headers.get('Accept', ''):
                        raise HTTPError(400, "No JSON object could be decoded")

                    # ex. key1=value2&key2=value2
                    try:
                        body = dict([(k, v[0] if len(v)==1 else v) for k, v in parse_qs(body, strict_parsing=True).items()])
                    except:
                        raise HTTPError(400, "Body was not able to be decoded")

            if urlargs and self.request.uri.find('?') > 0:
                # include url params
                body = dict([(k, v[0] if len(v)==1 else v) for k, v in self.request.arguments.items()])
            
            # catch the ValidationErrors in your _handle_request_exception method
            self.validated = parsed.validate(body)

            return method(self, *args, **kwargs)

        return validate
    return wrapper
