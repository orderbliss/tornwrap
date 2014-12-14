import re
from json import dumps
from tornado import escape
from decimal import Decimal
from datetime import datetime


def json_defaults(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return str(obj)
    elif hasattr(obj, 'json'):
        return obj.json()
    else:
        return repr(obj)


def json_encode(data):
    return dumps(data, default=json_defaults).replace('</', '<\\/')


escape.json_encode = json_encode


TOKENIZER = re.compile('"|(/\*)|(\*/)|(//)|\n|\r')
END_SLASHES_RE = re.compile(r'(\\)*$')


def json_minify(string, strip_space=True): # pragma: no cover
    """Removes whitespace from json strings, returning the string
    """
    in_string = False
    in_multi = False
    in_single = False

    new_str = []
    index = 0

    for match in re.finditer(TOKENIZER, string):

        if not (in_multi or in_single):
            tmp = string[index:match.start()]
            if not in_string and strip_space:
                # replace white space as defined in standard
                tmp = re.sub('[ \t\n\r]+', '', tmp)
            new_str.append(tmp)

        index = match.end()
        val = match.group()

        if val == '"' and not (in_multi or in_single):
            escaped = END_SLASHES_RE.search(string, 0, match.start())

            # start of string or unescaped quote character to end string
            if not in_string or (escaped is None or len(escaped.group()) % 2 == 0):
                in_string = not in_string
            index -= 1 # include " character in next catch
        elif not (in_string or in_multi or in_single):
            if val == '/*':
                in_multi = True
            elif val == '//':
                in_single = True
        elif val == '*/' and in_multi and not (in_string or in_single):
            in_multi = False
        elif val in '\r\n' and not (in_multi or in_string) and in_single:
            in_single = False
        elif not ((in_multi or in_single) or (val in ' \r\n\t' and strip_space)):
            new_str.append(val)

    new_str.append(string[index:])
    return ''.join(new_str)
