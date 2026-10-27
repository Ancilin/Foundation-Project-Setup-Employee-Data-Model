"""Domain exceptions raised by business services."""


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, error_code: str = "BAD_REQUEST", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class NotFoundError(AppException):
    def __init__(self, message: str, error_code: str = "NOT_FOUND"):
        super().__init__(message=message, error_code=error_code, status_code=404)


class ForbiddenError(AppException):
    def __init__(self, message: str, error_code: str = "FORBIDDEN"):
        super().__init__(message=message, error_code=error_code, status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str, error_code: str = "CONFLICT"):
        super().__init__(message=message, error_code=error_code, status_code=409)


class ValidationError(AppException):
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(message=message, error_code=error_code, status_code=422)
