import os
from time import time
from json import dumps

from . import logger

LOG_METRICS = os.getenv('LOG_METRICS', 'TRUE').upper()=='TRUE'

LIBRATO_USER = os.getenv('LIBRATO_USER')
LIBRATO_TOKEN = os.getenv('LIBRATO_TOKEN')
if (LIBRATO_USER, LIBRATO_TOKEN) != (None, None):
    import librato


class new(object):
    def __init__(self, name):
        self.name = name
        self._groups = {}
        self.start_time = time()

    def _to_logs(self):
        if LOG_METRICS:
            [[logger.log.info(dumps(dict(time=metric.now, 
                                  source=metric.source, 
                                  metric=".".join((self.name, group_name)), 
                                  value=metric.value))) \
              for metric in group._metrics.values()] for group_name, group in self._groups.items()]

    def _to_librato(self):
        if LIBRATO_USER and LIBRATO_TOKEN:
            try:
                api = librato.connect(LIBRATO_USER, LIBRATO_TOKEN)
                queue = api.new_queue()
                for group_name, group in self._groups.items():
                    for metric in group._metrics.values():
                        if metric.value is not None:
                            queue.add(".".join((self.name, group_name)), 
                                      metric.value,
                                      source=metric.source,
                                      measure_time=metric.now)
                queue.submit()
            except:
                logger.traceback()

    def submit(self):
        self._to_logs()
        self._to_librato()

    def __repr__(self):
        return dumps([[dict(time=metric.now, 
                            source=metric.source, 
                            metric=".".join((self.name, group_name)), 
                            value=metric.value) \
          for metric in group._metrics.values()] for group_name, group in self._groups.items()], indent=2, sort_keys=True)

    def __enter__(self):
        self.time = time()
        return self

    def __exit__(self, typ, value, traceback):
        self.submit()

    def __getattr__(self, name):
        return self._groups.get(name) \
               or self._groups.setdefault(name, _group(name, self.start_time))


class _group(object):
    def __init__(self, name, start_time):
        self.name = name
        self._metrics = {}
        self.start_time = start_time

    def __getattr__(self, source):
        return self._metrics[source].value
   
    def time(self, source):
        now = time()
        self._metrics[source] = _metric(source, int((now-self.start_time)*1000), now)
        self.start_time = now

    def incr(self, source, by=1):
        return (self._metrics.get(source) or self._metrics.setdefault(source, _metric(source))).incr(by)

class _metric(object):
    def __init__(self, source, value=0, now=None):
        self.source = source
        self.value = value
        self.now = int(now or time())

    def incr(self, by):
        self.value = self.value + by
        return self.value

    # def append(self, value):
    #     pass
