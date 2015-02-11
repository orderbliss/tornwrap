import re
import os
import sys
import inspect
import logging
from json import dumps
from decimal import Decimal
from datetime import datetime
from traceback import format_exception
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

DEBUG =          (str(os.getenv('DEBUG','FALSE')).upper() == 'TRUE')
FILTER_SECRETS = re.compile(r'(?P<key>\w*secret|token|auth|password\w*\=)(?P<secret>[^\&\s]+)')

if DEBUG:
    try:
        from pygments import highlight
        from pygments.lexers import JsonLexer
        from pygments.lexers import PythonLexer
        from pygments.formatters import TerminalFormatter
        python_lexer, json_lexer, formatter = PythonLexer(), JsonLexer(), TerminalFormatter()
    except:
        highlight = lambda a, b, c: a
        python_lexer, formatter = None, None

_log = logging.getLogger()


try:
    assert os.getenv('LOGENTRIES_TOKEN')
    from logentries import LogentriesHandler
    _log = logging.getLogger('logentries')
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))
    _log.addHandler(LogentriesHandler(os.getenv('LOGENTRIES_TOKEN')))
except:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    _log.addHandler(ch)
    _log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))


setLevel = _log.setLevel


def json_defaults(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return str(obj)
    else:
        return repr(obj)


def clean(data):
    return FILTER_SECRETS.sub(r'\g<key>=secret', data)


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
        sys.stdout.write(highlight("\n".join(d['traceback']), python_lexer, formatter))


def log(*args, **kwargs):
    try:
        d = dict()
        [d.update(a) for a in args]
        d.update(kwargs)
        _debug = kwargs.pop('debug') if 'debug' in kwargs else False
        if DEBUG:
            callerframerecord = inspect.stack()[1]
            info = inspect.getframeinfo(callerframerecord[0])
            _log.info("\033[90mLOG\033[0m %s \033[90m%s\033[0m via \033[95m%s()\033[0m" % (info.filename, str(info.lineno), info.function))
            _log.info(highlight(dumps(d, indent=2, sort_keys=True, default=json_defaults), json_lexer, formatter))
        else:
            _log.info(clean(dumps(d, default=json_defaults, sort_keys=True)))
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
                if DEBUG:
                    callerframerecord = inspect.stack()[1]
                    info = inspect.getframeinfo(callerframerecord[0])
                    _log.info("\033[90mDEBUG\033[0m %s \033[90m%s\033[0m via \033[95m%s()\033[0m: %s" % (info.filename, str(info.lineno), info.function, message))
                else:
                    _log.debug(message)
                return
            d['message'] = message
        [d.update(a) for a in args]
        d.update(kwargs)
        if DEBUG:
            callerframerecord = inspect.stack()[1]
            info = inspect.getframeinfo(callerframerecord[0])
            _log.info("\033[90mDEBUG\033[0m %s \033[90m%s\033[0m via \033[95m%s()\033[0m" % (info.filename, str(info.lineno), info.function))
            _log.info(highlight(dumps(d, indent=2, sort_keys=True, default=json_defaults), json_lexer, formatter))
        else:
            _log.debug(dumps(d, default=json_defaults))
    except:
        traceback()


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
        _log.fatal("%s%s"%(add, clean(dumps(_basics))))
    elif _basics['status'] > 399:
        _log.warn("%s%s"%(add, clean(dumps(_basics))))
    else:
        _log.info("%s%s"%(add, clean(dumps(_basics))))
