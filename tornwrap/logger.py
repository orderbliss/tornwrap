import re
import os
import sys
import logging
from json import dumps
import traceback as _traceback
from traceback import format_exception
from tornado.web import RedirectHandler
from tornado.web import StaticFileHandler

from tornwrap.helpers import json_defaults


FILTER_SECRETS = re.compile(r'(?P<key>\w*secret|token|auth|password|client_id\w*\=)(?P<secret>[^\&\s]+)').sub
DEBUG = (os.getenv('DEBUG') == 'TRUE')
LOGLVL = getattr(logging, os.getenv('LOGLVL', 'INFO'))

_log = logging.getLogger()
_log.setLevel(LOGLVL)


# add sys.stdout
stdout = logging.StreamHandler(sys.stdout)
stdout.setLevel(LOGLVL)
_log.addHandler(stdout)


try:
    assert os.getenv('LOGENTRIES_TOKEN')
    from logentries import LogentriesHandler
    le = LogentriesHandler(os.getenv('LOGENTRIES_TOKEN'))
    le.setLevel(LOGLVL)
    _log.addHandler(le)

except:  # pragma: no cover
    pass


setLevel = _log.setLevel


def traceback(exc_info=None, **kwargs):
    if not exc_info:
        exc_info = sys.exc_info()

    # if DEBUG and exc_info:  # pragma: no cover
    #     try:
    #         from pygments import highlight
    #         from pygments.lexers import get_lexer_by_name
    #         from pygments.formatters import TerminalFormatter

    #         tbtext = ''.join(_traceback.format_exception(*exc_info))
    #         lexer = get_lexer_by_name("pytb", stripall=True)
    #         formatter = TerminalFormatter()
    #         sys.stderr.write('\n\033[90mtornwrap.logger.traceback:\033[0m '+dumps(kwargs, indent=2, sort_keys=True)+'\n'+highlight(tbtext, lexer, formatter)+'\n')
    #         return
    #     except:
    #         pass

    try:
        kwargs['traceback'] = format_exception(*exc_info)

    except:
        _log.error('Unable to parse traceback %s: %s' % (type(exc_info), repr(exc_info)))

    _log.error(dumps(kwargs, default=json_defaults))


def log(**kwargs):
    try:
        kwargs = dumps(kwargs,
                       default=json_defaults,
                       sort_keys=True, indent=2 if DEBUG else None)
        if DEBUG:  # pragma: no cover
            try:
                from pygments import highlight
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import TerminalFormatter

                lexer = get_lexer_by_name("json", stripall=True)
                formatter = TerminalFormatter()
                sys.stderr.write('\n\033[90mtornwrap.logger.log:\033[0m '+highlight(kwargs, lexer, formatter)+'\n')
                return

            except:
                pass

        _log.info(kwargs)

    except:
        traceback()


def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        # dont log Statics/Redirects
        return

    data = dict(status=handler.get_status(),
                method=handler.request.method,
                url=FILTER_SECRETS(r'\g<key>=secret', handler.request.uri),
                reason=handler._reason,
                id=handler.request_id,
                ms="%.0f" % (1000.0 * handler.request.request_time()))

    data.update(handler.get_log_payload() or {})
    data.update(getattr(handler, '_log_error', {}))

    log(**data)
    if DEBUG:
        sys.stderr.write("\033[92m-------------------- End of Request --------------------\033[0m\n\n")
    return data
