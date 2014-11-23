import re
import valideer
import timestring


class boolean(valideer.Validator):
    name = "bool"
    true = ("y", "yes", "1", "t", "true", "on")
    false = ("n", "no", "0", "f", "false", "off")
    def validate(self, value, adapt=True):
        if type(value) is bool:
            return value
        _value = str(value).lower()
        if _value in self.true:
            return True if adapt else value
        elif _value in self.false:
            return False if adapt else value
        else:
            self.error("bool is not valid")

class timezone(valideer.String):
    name = "timezone"
    timezones = {
        "US/EASTERN": "US/Eastern", "EST": "US/Eastern",  "-4": "US/Eastern",
        "US/CENTRAL": "US/Central", "CST": "US/Central", "-5": "US/Central",
        "US/MOUNTAIN": "US/Mountain", "MST": "US/Mountain", "-6": "US/Mountain",
        "US/PACIFIC": "US/Pacific", "PST": "US/Pacific", "-7": "US/Pacific",
        "UTC": "UTC", "+0": "UTC", "0": "UTC", "-0": "UTC"
    }
    def validate(self, value, adapt=True):
        super(timezone, self).validate(value)
        result = self.timezones.get(value.upper())
        if result:
            return result if adapt else value
        else:
            raise valideer.ValidationError("invalid timezoe", value)

class uuid(valideer.Pattern):
    name = "uuid"    
    regexp = re.compile(r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")

class _id(valideer.Pattern):
    name = "id"
    regexp = re.compile(r"^[1-9]\d*$")
    def validate(self, value, adapt=True):
        super(_id, self).validate(str(value))
        return int(value)

class email(valideer.Pattern):
    name = "email"
    regexp = re.compile(r".+@.+\..+", re.I)
    def validate(self, value, adapt=True):
        super(email, self).validate(value)
        return value.lower() if adapt else value

class branch(valideer.Pattern):
    name = "branch"
    regexp = re.compile(r"^[\w\-\.\/\*\=\+\@\#\$\%\,\&\:\;]{1,255}$")

class commit(valideer.Pattern):
    name = "commit"
    regexp = re.compile(r"^\w{40}$")
    def validate(self, value, adapt=True):
        super(commit, self).validate(value)
        return str(value).lower()

class ref(valideer.AnyOf):
    name = "ref"
    _validators = map(valideer.parse, ("branch", "commit"))
    def __init__(self): pass

class version(valideer.Pattern):
    name = "version"
    regexp = re.compile(r"^\d+\.\d+\.\d+$")

class _callable(valideer.Validator):
    name = "callable"
    def validate(self, value, adapt=True):
        if not callable(value):
            self.error("value must be callable")
        return value

class date(valideer.Validator):
    name = "date"
    def validate(self, value, adapt=True):
        try:
            date = timestring.Date(value)
            return date if adapt else value
        except timestring.TimestringInvalid:
            self.error("invalid date provied")

class range(valideer.Validator):
    name = "daterange"
    def validate(self, value, adapt=True):
        try:
            _range = timestring.Range(value)
            return _range if adapt else value
        except timestring.TimestringInvalid:
            self.error("invalid date range provied")

class day(valideer.String):
    name = "day"
    def validate(self, value, adapt=True):
        super(day, self).validate(str(value))
        if str(value) in tuple("0123456"):
            return int(value)
        else:
            value = str(value).lower()
            for i, _day in ((0, "sun"), (1, "mon"), (2, "tue"), (3, "wed"), (4, "thu"), (5, "fri"), (6, "sat")):
                if value.startswith(_day):
                    return i
            raise valideer.ValidationError("invalid value")

class rangetz(valideer.Validator):
    name = "daterangetz"
    def validate(self, value, adapt=True):
        try:
            if isinstance(value, timestring.Range):
                if value.tz is None:
                    value.tz = "UTC"
                return value
            return timestring.Range(value, tz="UTC")
        except timestring.TimestringInvalid:
            raise valideer.ValidationError("Invalid range provied")

class elapse(valideer.String):
    name = "elapse"
    def validate(self, value, adapt=True):
        super(elapse, self).validate(str(value))
        return str(len(timestring.Range(value)))

class _float(valideer.Validator):
    name = "float"
    regexp = re.compile(r"\-?\d+(\,\d{3})*(\.\d+)?(k|m)?")
    def validate(self, value, adapt=True):
        if type(value) in (float, int, long):
            return float(value)
        if not self.regexp.match(value):
            raise valideer.ValidationError("invalid characters found")
        x = 1000 if value.endswith('k') else 1000000 if value.endswith('m') else 1
        if x > 1:
            value = value[:-1]
        try:
            value = float(value) * x
            return value
        except ValueError:
            raise valideer.ValidationError("Value must be a valid number")

class integar(valideer.String):
    name = "int"
    regexp = re.compile(r"^(\d+(\.\d+)?\%|(\-?\d+(\,\d{3})*(\.\d+)?(k|m)?))$")
    def validate(self, value, adapt=True):
        if type(value) is int:
            return value
        else:
            value = str(value)
        if not self.regexp.match(value):
            raise valideer.ValidationError("invalid characters found")
        x = 1000 if value.endswith('k') else 1000000 if value.endswith('m') else 1
        if x > 1:
            value = value[:-1]
        if value.endswith('%'):
            return value
        try:
            return int(float(value) * x)
        except ValueError:
            raise valideer.ValidationError("Value must be a valid number")

class cc_name(valideer.Pattern):
    name = "cc_name"
    regexp = re.compile(r"^.{1,50}$")

class cc_cvc(valideer.Pattern):
    name = "cc_cvc"
    regexp = re.compile(r"^\d{3,4}$")

class cc_exp_month(valideer.Pattern):
    name = "cc_exp_month"
    regexp = re.compile(r"^\d{1,2}$")

class cc_exp_year(valideer.Pattern):
    name = "cc_exp_year"
    regexp = re.compile(r"^\d{4}$")

class cc_number(valideer.Pattern):
    name = 'cc_number'
    regexp = re.compile(r"^\d{15,16}$")
