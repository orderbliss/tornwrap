from time import time
from sys import stdout

from tornwrap import logger


class timeit:
    __slots__ = ('d', )

    def __init__(self, name, source=None, **extra_data):
        self.d = (("source=%s " % source) if source else "", name, time(), extra_data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        speed = int((time() - self.d[2]) * 1000)
        stdout.write("%smeasure#%s.speed=%dms\n" % (self.d[0], self.d[1], speed))
        if self.d[3]:
            logger.log(name=self.d[1], source=self.d[0][7:], speed=speed, **self.d[3])


class event:
    __slots__ = ('d', )

    def __init__(self, name, title, threshold=None, **data):
        self.d = [name, title, data, time(), threshold or 0]

    def __enter__(self):
        return self

    def cancel(self):
        self.d = None

    def set(self, index, value):
        self.d[2][index] = value

    def __exit__(self, *args):
        if self.d:
            end = time()
            start = self.d[3]
            speed = int((end - start) * 1000)
            if speed > self.d[4]:
                data = self.d[2]
                data['speed'] = '%dms' % speed
                data = ' '.join([('%s=%s' % tuple(map(str, d))) for d in data.iteritems()])
                stdout.write('event#%s="%s" description="%s" start_time=%d, end_time=%d\n' %
                             (self.d[0], self.d[1], data, int(start), int(end)))


def metric(m):
    # required to properly write to stdout in Celery
    stdout.write(m)
