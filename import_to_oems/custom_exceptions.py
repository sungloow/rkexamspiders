class CustomBaseException(Exception):
    def __init__(self, message, method_name, line_number):
        self.message = message
        self.method_name = method_name
        self.line_number = line_number

    def __str__(self):
        return f"[Error] {self.message}\nIn function '{self.method_name}', line {self.line_number}"


class UserError(CustomBaseException):
    def __init__(self, message, method_name, line_number):
        super().__init__(message, method_name, line_number)


# 数据库操作异常
class DBError(CustomBaseException):
    def __init__(self, message, method_name, line_number):
        super().__init__(message, method_name, line_number)


# Duplicate entry
class DuplicateEntryError(DBError):
    def __init__(self, message, method_name, line_number):
        super().__init__(message, method_name, line_number)

