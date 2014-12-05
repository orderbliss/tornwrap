import os
import sys
import logging
from json import dumps
from decimal import Decimal
from datetime import datetime
from traceback import format_exception
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

DEBUG = (os.getenv('DEBUG') == 'TRUE')
if DEBUG:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter
    lexer, formatter = PythonLexer(), TerminalFormatter()

_log = logging.getLogger()


if os.getenv('LOGENTRIES_TOKEN'):
    from logentries import LogentriesHandler
    _log = logging.getLogger('logentries')
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))
    _log.addHandler(LogentriesHandler(os.getenv('LOGENTRIES_TOKEN')))

else:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    _log.addHandler(ch)
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))


def json_defaults(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return str(obj)
    else:
        return repr(obj)
    

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
    if DEBUG:
        sys.stdout.write(highlight("\n".join(d['traceback']), lexer, formatter))


def log(*args, **kwargs):
    try:
        d = dict()
        [d.update(a) for a in args]
        d.update(kwargs)
        debug = kwargs.pop('debug') if 'debug' in kwargs else False
        _log.info(dumps(d, default=json_defaults))
        if debug:
            _log.debug(dumps(debug, default=json_defaults))
    except:
        traceback()


def debug(*args, **kwargs):
    try:
        d = dict()
        [d.update(a) for a in args]
        d.update(kwargs)
        _log.debug(dumps(d, default=json_defaults))
    except:
        traceback()


setLevel = _log.setLevel

def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        return

    # Build log json
    _basics = {"status":    handler.get_status(),
               "method":    handler.request.method,
               "uri":       handler.request.uri,
               "reason":    handler._reason,
               "ms":        "%.0f" % (1000.0 * handler.request.request_time())}

    if hasattr(handler, '_rollbar_token'):
        _basics["rollbar"] = handler._rollbar_token
    if hasattr(handler, 'get_log_payload'):
        _basics.update(handler.get_log_payload() or {})

    add = ""
    if (os.getenv('DEBUG') == 'TRUE'):
        if _basics['status'] >= 500:
            add = "\033[91m%(method)s %(status)s\033[0m " % _basics
        elif _basics['status'] >= 400:
            add = "\033[93m%(method)s %(status)s\033[0m " % _basics
        else:
            add = "\033[92m%(method)s %(status)s\033[0m " % _basics
        
    if _basics['status'] > 499:
        _log.fatal("%s%s"%(add, dumps(_basics)))
    elif _basics['status'] > 399:
        _log.warn("%s%s"%(add, dumps(_basics)))
    else:
        _log.info("%s%s"%(add, dumps(_basics)))
