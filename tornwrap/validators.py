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

class uuid(valideer.Pattern):
    name = "uuid"    
    regexp = re.compile(r"^[0-9a-f]{8}(-?[0-9a-f]{4}){3}-?[0-9a-f]{12}$")

class email(valideer.Pattern):
    name = "email"
    regexp = re.compile(r".+@.+\..+", re.I)
    def validate(self, value, adapt=True):
        super(email, self).validate(value)
        return value.lower() if adapt else value

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
