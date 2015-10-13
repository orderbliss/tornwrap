import re
import os
import sys
import logging
from json import dumps
from traceback import format_exception
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

from .helpers import json_defaults

FILTER_SECRETS = re.compile(r'(?P<key>\w*secret|token|auth|password|client_id\w*\=)(?P<secret>[^\&\s]+)').sub

_log = logging.getLogger()


try:
    assert os.getenv('LOGENTRIES_TOKEN')
    from logentries import LogentriesHandler
    _log = logging.getLogger('logentries')
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))
    _log.addHandler(LogentriesHandler(os.getenv('LOGENTRIES_TOKEN')))

except:  # pragma: no cover
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    _log.addHandler(ch)
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))


setLevel = _log.setLevel


def traceback(exc_info=None, *args, **kwargs):
    if not exc_info:
        exc_info = sys.exc_info()
    d = dict()
    [d.update(a) for a in args]
    d.update(kwargs)
    try:
        d['traceback'] = format_exception(*exc_info)
    except:
        _log.error('Unable to parse traceback %s: %s' % (type(exc_info), repr(exc_info)))
    _log.error(dumps(d, default=json_defaults))


def log(*args, **kwargs):
    try:
        d = dict()
        [d.update(a) for a in args]
        d.update(kwargs)
        _debug = kwargs.pop('debug') if 'debug' in kwargs else False
        _log.info(dumps(d, default=json_defaults, sort_keys=True))
        if _debug:
            debug(_debug)
    except:
        traceback()


def debug(message=None, *args, **kwargs):
    try:
        d = dict()
        if isinstance(message, dict):
            d.update(message)
        elif message:
            if not args and not kwargs:
                _log.debug(message)
                return
            d['message'] = message
        [d.update(a) for a in args]
        d.update(kwargs)
        _log.debug(dumps(d, default=json_defaults))
    except:
        traceback()


def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        # dont log Statics/Redirects
        return

    # Build log json
    _basics = {"status":    handler.get_status(),
               "method":    handler.request.method,
               "url":       FILTER_SECRETS(r'\g<key>=secret', handler.request.uri),
               "reason":    handler._reason,
               "ms":        "%.0f" % (1000.0 * handler.request.request_time())}

    if hasattr(handler, 'get_log_payload'):
        _basics.update(handler.get_log_payload() or {})

    getattr(_log, 'fatal' if _basics['status'] > 499 else 'warn' if _basics['status'] > 399 else 'info')(dumps(_basics))
    return _basics
