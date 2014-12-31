from json import loads
from functools import wraps
from tornado.web import HTTPError
from valideer import ValidationError


def endpoint(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Require SSL
        # -----------
        if not getattr(self, 'debug', False) and self.request.headers.get('X-Forwarded-Port') == '80': #pragma: no cover
            if self.request.method == 'GET':
                self.redirect("https://%s%s" % (self.request.host, self.request.uri))
                return
            else:
                raise HTTPError(403, reason='ssl endpoint required')
        
        self.body = {}
        self.query = {}
        self._rollbar_token = None

        method = self.request.method.lower()
        endpoint = getattr(self, 'endpoint')
        if not endpoint:
            raise HTTPError(404 if method == 'get' else 405)

        endpoint = endpoint.get(method, False)
        if endpoint is False:
            raise HTTPError(405)

        if endpoint.get('guest', False) is False:
            # Authorization
            # -------------
            if not self.current_user:
                raise HTTPError(401)

            #  Privileges
            # -------------
            if '*' not in getattr(self.current_user, "scope", ['*']):
                resource = "_".join((self.resource, method))
                if resource not in self.current_user.scope and ("*_%s" % self.request.method.lower()) not in self.current_user.scope:
                    raise HTTPError(401, reason="permission denied to resource at %s"%resource)

        # Validation
        # ----------
        validate_body = endpoint.get('body')
        if validate_body:
            try:
                self.body = validate_body(loads(self.request.body or '{}'))
            except ValidationError:
                raise
            except ValueError as e:
                raise HTTPError(400, str(e), reason="Transaction rejected. Requst was not formatted properly.")

        # Query
        # -----
        query = dict([(k, v[0] if len(v)==1 else v) for k, v in self.request.query_arguments.items() if v!=['']]) if self.request.query_arguments else {}
        query.pop('access_token', False)
        query.pop('_', None) # ?_=1417978116609
        validate_query = endpoint.get('query')
        self.query = validate_query(query) if validate_query else query

        return func(self, *args, **kwargs)

    return wrapper
