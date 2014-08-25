from functools import wraps
from base64 import decodestring
from tornado.web import HTTPError


def authenticated(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        auth_header = self.request.headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Basic '):
            self.set_status(401)
            self.set_header('WWW-Authenticate', 'Basic realm=Restricted')
            self.finish()
            return False
        self.current_user = self.get_authenticated_user(*tuple(decodestring(auth_header[6:]).split(':',1)))
        if not self.current_user:
            raise HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper
