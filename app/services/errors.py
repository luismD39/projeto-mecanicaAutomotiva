"""Erros de negócio. Os serviços lançam estes erros; app/errors.py os converte em resposta HTTP."""


class AppError(Exception):
    status = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, fields: dict | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.fields = fields
        if code:
            self.code = code


class ValidationError(AppError):
    status = 422
    code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status = 409
    code = "CONFLICT"
