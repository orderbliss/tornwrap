import os
import sys
import logging
from json import dumps
from tornado.log import access_log
from traceback import format_exception
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

log = access_log

if os.getenv('LOGENTRIES_TOKEN'):
    from logentries import LogentriesHandler
    log = logging.getLogger('logentries')
    log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))
    log.addHandler(LogentriesHandler(os.getenv('LOGENTRIES_TOKEN')))

def traceback(exc_info=None, **kwargs):
    # raise_exc_info(exc_info=(type, value, traceback))
    if not exc_info:
        exc_info = sys.exc_info()
    kwargs['traceback'] = format_exception(*exc_info)
    log.error(dumps(kwargs))
    log.debug("\n".join(kwargs['traceback']))

def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        return

    # Build log json
    _log = {"status":    handler.get_status(),
            "method":    handler.request.method,
            "uri":       handler.request.uri,
            "reason":    handler._reason,
            "ms":        "%.0f" % (1000.0 * handler.request.request_time())}

    if hasattr(handler, '_rollbar_token'):
        _log["rollbar"] = handler._rollbar_token
    if hasattr(handler, 'get_log_payload'):
        _log.update(handler.get_log_payload() or {})

    add = ""
    if (os.getenv('DEBUG') == 'TRUE'):
        if _log['status'] >= 500:
            add = "\033[91m%(method)s %(status)s\033[0m " % _log
        elif _log['status'] >= 400:
            add = "\033[93m%(method)s %(status)s\033[0m " % _log
        else:
            add = "\033[92m%(method)s %(status)s\033[0m " % _log
        
    if _log['status'] > 499:
        log.fatal("%s%s"%(add, dumps(_log)))
    elif _log['status'] > 399:
        log.warn("%s%s"%(add, dumps(_log)))
    else:
        log.info("%s%s"%(add, dumps(_log)))
