import re
import valideer


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
