import os
from time import time

# LIBRATO = os.getenv('LIBRATO_USER'), os.getenv('LIBRATO_TOKEN')
# if LIBRATO != (None, None):
#     import librato


class new(object):
    def __init__(self, name):
        self.name = name
        self._groups = {}

    def _to_logs(self):
        pass

    def _to_librato(self):
        if False: # wip
            api = librato.connect(*LIBRATO)
            queue = api.new_queue()
            for group in self:
                for metric in group:
                    queue.add(".".join((self.name, metric.group)), 
                              metric.value, 
                              source=metric.source, 
                              measure_time=metric.now)
            queue.submit()

    def submit(self):
        self._to_logs()
        self._to_librato()

    def __enter__(self):
        self.time = time()
        return self

    def __exit__(self, typ, value, traceback):
        self.submit()

    def __getattr__(self, name):
        return self._groups.get(name) \
               or self._groups.setdefault(name, _group(name))

    def __iter__(self):
        return self._groups.values()


class _group(object):
    def __init__(self, name):
        self.name = name
        self._metrics = {}
        self.now = time()

    def __getattr__(self, source):
        return self._metrics[source].value
   
    def __iter__(self):
        return self._metrics.values()

    def time(self, source):
        now = time()
        self._metrics[source] = _metric(source, (now-self.now)*1000, now)
        self.now = now

    def incr(self, source, by=1):
        return (self._metrics.get(source) or self._metrics.setdefault(source, _metric(source))).incr(by)

    # def append(self, source, value):
    #     (self._metrics.get(source) or self._metrics.setdefault(source, _metric(source))).append(value)


class _metric(object):
    def __init__(self, source, value=0, now=None):
        self.source = source
        self.value = value
        self.now = now or time()

    def incr(self, by):
        self.value = self.value + by
        return self.value

    # def append(self, value):
    #     pass
