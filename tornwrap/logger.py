import os
import logging
from json import dumps
from tornado.log import access_log
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

log = access_log

if os.getenv('LOGENTRIES_TOKEN'):
    from logentries import LogentriesHandler
    log = logging.getLogger('logentries')
    log.setLevel(getattr(logging, os.getenv('LOGLVL', "INFO")))
    log.addHandler(LogentriesHandler(os.getenv('LOGENTRIES_TOKEN')))


def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        return

    # Build log json
    _log = {"status":    handler.get_status(),
            "method":    handler.request.method,
            "uri":       handler.request.uri,
            "reason":    handler._reason,
            "ms":        "%.0f" % (1000.0 * handler.request.request_time())}

    if handler.current_user:
        _log["user"] = handler.current_user.id
    if hasattr(handler, '_rollbar_token'):
        _log["rollbar"] = handler._rollbar_token

    add = ""
    if (os.getenv('DEBUG') == 'TRUE'):
        if _log['status'] >= 500:
            add = "\033[91m%(method)s %(status)s\033[0m " % _log
        elif _log['status'] >= 400:
            add = "\033[93m%(method)s %(status)s\033[0m " % _log
        else:
            add = "\033[92m%(method)s %(status)s\033[0m " % _log
        
    if _log['status'] > 499:
        log.fatal("%s: %s"%(add, dumps(_log, separators=(',',':'))))
    elif _log['status'] > 399:
        log.warn("%s: %s"%(add, dumps(_log, separators=(',',':'))))
    else:
        log.info("%s: %s"%(add, dumps(_log, separators=(',',':'))))