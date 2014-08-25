import urlparse
from valideer import parse
from functools import wraps
from tornado.web import HTTPError
from valideer import ValidationError
from tornado.escape import json_decode


def validated(schema, params=True, additional_properties=False):
    parsed = parse(schema, additional_properties=additional_properties)
    def wrapper(method):
        @wraps(method)
        def validate(self, *args, **kwargs):
            print "\033[92m....\033[0m", self.request.arguments
            if self.request.method in ('GET', 'DELETE'):
                # include url params
                body = dict([(k, v[0] if len(v)==1 else v) for k, v in self.request.arguments.items()])
            else:
                body = self.request.body
                if body:
                    try:
                        body = json_decode(body)
                    except:
                        # ex. key1=value2&key2=value2
                        try:
                            body = dict([(k, v[0] if len(v)==1 else v) for k, v in urlparse.parse_qs(body).items()])
                        except:
                            body = {}

            try:
                self.validated = parsed.validate(body)
            except ValidationError as e:
                raise HTTPError(400, str(e))
            else:
                return method(self, *args, **kwargs)

        return validate
    return wrapper
