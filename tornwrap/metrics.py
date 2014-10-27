from time import time


class speed:
    def __init__(self, metric_name, redis=None):
        self.metric_name = metric_name
        self.redis = redis

    def __enter__(self):
        self.start = time()

    def __exit__(self, typ, value, traceback):
        self.redis.rpush(self.metric_name, (time()-self.start)*1000)


class incr:
    def __init__(self, success=None, error=None, redis=None):
        self.metric_name = (success, error)
        self.redis = redis

    def __enter__(self):
        pass

    def __exit__(self, typ, value, traceback):
        key = self.metric_name[(0 if typ is None else 1)]
        if key:
            self.redis.incr(key)
