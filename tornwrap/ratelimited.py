import time
import functools
from tornado.web import HTTPError


def ratelimited(user=None, guest=None, format="tornrate:%s"):
    """Rate limit decorator

    ### Headers
    X-RateLimit-Limit: 1000
    X-RateLimit-Remaining: 567
    X-RateLimit-Reset: 1242711173

    ### Status when rate limited
    Status: 403 Forbidden

    """
    try:
        import redis
    except ImportError: # pragma: no cover
        raise ImportError("redis is required to use torndown.ratelimtied")

    if user:
        assert type(user[0]) is int and user[0] > 0, "user[0] must be int and > 0"
        assert type(user[1]) is int and user[1] > 0, "user[1] must be int and > 0"
    else:
        user = (None, None)

    if guest:
        assert type(guest[0]) is int and guest[0] > 0, "guest[0] must be int and > 0"
        assert type(guest[1]) is int and guest[1] > 0, "guest[1] must be int and > 0"
    else:
        guest = (None, None)

    def wrapper(method):
        @functools.wraps(method)
        def limit(self, *args, **kwargs):
            tokens, refresh = user if self.current_user else guest
            if tokens is None:
                return method(self, *args, **kwargs)
                
            # --------------
            # Get IP Address
            # --------------
            # http://www.tornadoweb.org/en/stable/httputil.html?highlight=remote_ip#tornado.httputil.HTTPServerRequest.remote_ip
            remote_ip = self.request.remote_ip
            mktime = int(time.mktime(time.localtime()))
            key = format % remote_ip

            # ----------------
            # Check Rate Limit
            # ----------------
            current = self.redis.get(key)
            if current is None:
                self.redis.setex(key, tokens-1, refresh)
                remaining, ttl = tokens-1, refresh
            else:
                remaining, ttl = int(self.redis.decr(key)), int(self.redis.ttl(key))

            # set headers
            self.set_header("X-RateLimit-Limit", tokens)
            self.set_header("X-RateLimit-Remaining", (0 if remaining < 0 else remaining))
            self.set_header("X-RateLimit-Reset", mktime+ttl)

            if remaining < 0:
                if hasattr(self, 'was_rate_limited'):
                    return self.was_rate_limited(tokens, (0 if remaining < 0 else remaining), mktime+ttl)
                else:
                    # Generic Exception
                    # IMPORTANT headers are reset according to RequestHandler.send_error 
                    # read more at http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.send_error
                    raise HTTPError(403, "rate-limited")

            # Continue with method
            return method(self, *args, **kwargs)

        return limit

    return wrapper
