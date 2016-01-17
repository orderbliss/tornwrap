import re
from valideer import *
import timestring


class boolean(Validator):
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


class timezone(String):
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
            self.error("invalid timezone")


class uuid(Pattern):
    name = "uuid"
    regexp = re.compile(r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")


class _id(Pattern):
    name = "id"
    regexp = re.compile(r"^[1-9]\d*$")

    def validate(self, value, adapt=True):
        super(_id, self).validate(str(value))
        return int(value) if adapt else value


class url(Pattern):
    name = "url"
    regexp = re.compile(r"^(https?:\/\/)")


class _file(String):
    name = "file"

    def validate(self, value, adapt=True):
        super(_file, self).validate(value, adapt)
        _value = os.path.join(os.getcwd(), value)
        if not os.path.exists(_value):
            raise ValidationError('unable to locate file at ' + _value)
        return _value if adapt else value


class branch(String):
    name = "branch"

    def validate(self, value, adapt=True):
        super(branch, self).validate(value, adapt)
        if value[:7] == 'origin/':
            return value[7:]
        elif value[:11] == 'refs/heads/':
            return value[11:]
        return value


class handler(Pattern):
    name = "handler"
    regexp = re.compile(r"^[\w\-\.]{1,255}$")


class slug(Pattern):
    name = "slug"
    regexp = re.compile(r"^[\w\-\.]{1,255}\/[\w\-\.]{1,255}$")


class email(Pattern):
    name = "email"
    regexp = re.compile(r".+@.+\..+", re.I)

    def validate(self, value, adapt=True):
        super(email, self).validate(value)
        return value.lower() if adapt else value


class percent(Pattern):
    name = 'percent'
    regexp = re.compile(r"^\d{1,3}(\.\d{1,2})?\%?$")

    def validate(self, value, adapt=True):
        super(percent, self).validate(value)
        if adapt:
            try:
                return float(value.replace('%', ''))
            except:
                return float(value)

        return value


class commit(Pattern):
    name = "commit"
    regexp = re.compile(r"^\d+:\w{12}|\w{40}$")

    def validate(self, value, adapt=True):
        super(commit, self).validate(value)
        return str(value).lower()


class ref(Validator):
    name = "ref"
    validate = AnyOf("branch", "commit").validate


class version(Pattern):
    name = "version"
    regexp = re.compile(r"^\d+\.\d+\.\d+$")


class _callable(Validator):
    name = "callable"

    def validate(self, value, adapt=True):
        if not callable(value):
            self.error("value must be callable")
        return value


class date(Validator):
    name = "date"

    def validate(self, value, adapt=True):
        try:
            date = timestring.Date(value)
            return date if adapt else value
        except timestring.TimestringInvalid as e:
            self.error("invalid date provied, %s" % str(e))


class date_past(Validator):
    name = "date-past"

    def validate(self, value, adapt=True):
        try:
            date = timestring.Date((value + " ago") if isinstance(value, (str, unicode)) else value)
            return date if adapt else value
        except timestring.TimestringInvalid as e:
            self.error("invalid date provied, %s" % str(e))


class range(Validator):
    name = "daterange"

    def validate(self, value, adapt=True):
        try:
            _range = timestring.Range(value)
            return _range if adapt else value
        except timestring.TimestringInvalid:
            self.error("invalid date range provied")


class day(String):
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
            self.error("invalid value")


class rangetz(Validator):
    name = "daterangetz"

    def validate(self, value, adapt=True):
        try:
            if isinstance(value, timestring.Range):
                if value.tz is None:
                    value.tz = "UTC"
                return value
            return timestring.Range(value, tz="UTC")
        except timestring.TimestringInvalid:
            self.error("Invalid range provied")


class elapse(String):
    name = "elapse"

    def validate(self, value, adapt=True):
        super(elapse, self).validate(str(value))
        return str(len(timestring.Range(value)))


class _float(Validator):
    name = "float"
    regexp = re.compile(r"\-?\d+(\,\d{3})*(\.\d+)?(k|m)?")

    def validate(self, value, adapt=True):
        if type(value) in (float, int, long):
            return float(value)
        elif type(value) not in (str, unicode):
            self.error("invalid type")
        if not self.regexp.match(value):
            self.error("invalid characters found")
        x = 1000 if value.endswith('k') else 1000000 if value.endswith('m') else 1
        if x > 1:
            value = value[:-1]
        try:
            value = float(value) * x
            return value
        except ValueError:
            self.error("Value must be a valid number")


class integar(String):
    name = "int"
    regexp = re.compile(r"^(\d+(\.\d+)?\%|(\-?\d+(\,\d{3})*(\.\d+)?(k|m)?))$")

    def validate(self, value, adapt=True):
        if type(value) is int:
            return value
        else:
            value = str(value)
        if not self.regexp.match(value):
            self.error("invalid characters found")
        x = 1000 if value.endswith('k') else 1000000 if value.endswith('m') else 1
        if x > 1:
            value = value[:-1]
        if value.endswith('%'):
            return value
        try:
            return int(float(value) * x)
        except ValueError:
            self.error("Value must be a valid number")


class cc_name(Pattern):
    name = "cc_name"
    regexp = re.compile(r"^.{1,50}$")


class cc_cvv(Pattern):
    name = "cc_cvv"
    regexp = re.compile(r"^\d{3,4}$")


class cc_exp_month(Pattern):
    name = "cc_exp_month"
    regexp = re.compile(r"^\d{1,2}$")


class cc_exp_year(Pattern):
    name = "cc_exp_year"
    regexp = re.compile(r"^\d{4}$")


class cc_number(Pattern):
    name = 'cc_number'
    regexp = re.compile(r"^\d{4}(\-|\s)?\d{4}(\-|\s)?\d{4}(\-|\s)?\d{2,4}$")
    replace = re.compile(r"[\D]")

    def validate(self, value, adapt=True):
        result = super(cc_number, self).validate(str(value))
        nv = self.replace.sub('', str(result))
        return nv if adapt else value
