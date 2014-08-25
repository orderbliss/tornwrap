import time
import functools
from tornado.web import HTTPError
from tornado.netutil import is_valid_ip


def ratelimited(user=None, guest=None, callback=None, format="tornrate:%s"):
    """Rate limit decorator

    :callback (str) name of the function to call when ratelimited
        getattr(handler, callback)()

    ### Headers
    X-RateLimit-Limit: 5000
    X-RateLimit-Remaining: 4999
    X-RateLimit-Reset: 1372700873

    ### Status
    Status: 403 Forbidden


    Usage
    -----

        def MyHanlder(tornado.web.RequestHandler):
            @property
            def redis(self):
                return self.application.redis

            # rate limit 5000/hour
            @ratelimited(5000, 3600)
            def get(self):
                self.finsh('Accepted Request')

    """
    if user:
        assert type(user[0]) is int and user[0] > 0, "user[0] must be int and > 0"
        assert type(user[1]) is int and user[1] > 0, "user[1] must be int and > 0"

    if guest:
        assert type(guest[0]) is int and guest[0] > 0, "guest[0] must be int and > 0"
        assert type(guest[1]) is int and guest[1] > 0, "guest[1] must be int and > 0"

    def wrapper(method):
        @functools.wraps(method)
        def limit(self, *args, **kwargs):
            redis = getattr(self, "redis", None)

            # --------------
            # Get IP Address
            # --------------
            # http://www.tornadoweb.org/en/stable/httputil.html?highlight=remote_ip#tornado.httputil.HTTPServerRequest.remote_ip
            remote_ip = self.request.remote_ip
            if not is_valid_ip(remote_ip):
                raise HTTPError(403, "not-valid-ip")

            mktime = int(time.mktime(time.localtime()))
            key = format % remote_ip
            tokens, refresh = user if self.current_user else guest

            # ----------------
            # Check Rate Limit
            # ----------------
            current = redis.get(key)
            if current is None:
                redis.setex(key, tokens-1, refresh)
                remaining, ttl = tokens-1, refresh
            elif current:
                remaining, ttl = int(redis.decr(key)), int(redis.ttl(key))

            # set headers
            self.set_header("X-RateLimit-Limit", tokens)
            self.set_header("X-RateLimit-Remaining", (0 if remaining < 0 else remaining))
            self.set_header("X-RateLimit-Reset", mktime+ttl)

            if remaining < 0:
                if callback:
                    return getattr(self, callback)(tokens, (0 if remaining < 0 else remaining), mktime+ttl)

                # Generic Exception
                # IMPORTANT headers are reset according to RequestHandler.send_error 
                # read more at http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.send_error
                raise HTTPError(403, "rate-limited")

            # Continue with method
            return method(self, *args, **kwargs)

        return limit

    return wrapper
