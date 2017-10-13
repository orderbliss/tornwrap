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

_log = logging.getLogger('tornado')


def traceback(exc_info=None, **kwargs):
    if not exc_info:
        exc_info = sys.exc_info()

    try:
        kwargs['traceback'] = format_exception(*exc_info)

    except:
        _log.error('Unable to parse traceback %s: %s' % (type(exc_info), repr(exc_info)))

    _log.error(dumps(kwargs, default=json_defaults))


def handler(handler):
    if isinstance(handler, (StaticFileHandler, RedirectHandler)):
        # dont log Statics/Redirects
        return

    status = handler.get_status()
    data = dict(status=status,
                method=handler.request.method,
                url=FILTER_SECRETS(r'\g<key>=secret', handler.request.uri),
                reason=handler._reason,
                ms="%.0f" % (1000.0 * handler.request.request_time()))

    data.update(handler.get_log_payload() or {})
    data.update(getattr(handler, '_log_error', {}))
    data = dumps(
        data,
        default=json_defaults,
        sort_keys=True,
        indent=2 if DEBUG else None
    )

    if status >= 500:
        _log.error(data)
    elif status >= 400:
        _log.warn(data)
    else:
        _log.info(data)

    return data
