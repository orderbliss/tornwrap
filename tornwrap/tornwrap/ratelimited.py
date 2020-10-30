import functools


def ratelimited(user=None, guest=None, redis_key_format="ratelimited.%s"):
    """Rate limit decorator

    ### Headers
    X-RateLimit-Limit: 1000
    X-RateLimit-Remaining: 567
    X-RateLimit-Reset: 1242711173

    ### Status when rate limited
    Status: 403 Forbidden

    """
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
            redis_key = redis_key_format % self.request.remote_ip

            # ----------------
            # Check Rate Limit
            # ----------------
            r = self.redis
            current = r.get(redis_key)
            if current is None:
                r.setex(redis_key, tokens-1, refresh)
                remaining, ttl = tokens-1, refresh
            else:
                remaining, ttl = int(r.decr(redis_key) or 0), int(r.ttl(redis_key) or 0)

            # set headers
            self.set_header("X-RateLimit-Limit", tokens)
            self.set_header("X-RateLimit-Remaining", (0 if remaining < 0 else remaining))
            self.set_header("X-RateLimit-Reset", ttl)

            if remaining < 0:
                do_continue = self.was_rate_limited(tokens, (0 if remaining < 0 else remaining), ttl)
                if do_continue is not True:
                    return

            # Continue with method
            return method(self, *args, **kwargs)

        return limit

    return wrapper
