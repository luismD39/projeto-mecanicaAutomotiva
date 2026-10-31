"""Respostas de erro: JSON para /api (formato de API_SPEC.md) e página HTML para as telas."""

import logging

from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.services.errors import AppError

logger = logging.getLogger(__name__)

MESSAGES = {
    400: ("BAD_REQUEST", "Requisição inválida."),
    404: ("NOT_FOUND", "Recurso não encontrado."),
    405: ("METHOD_NOT_ALLOWED", "Método HTTP não permitido para este endereço."),
    422: ("VALIDATION_ERROR", "Verifique os campos informados."),
    500: ("INTERNAL_ERROR", "Erro interno no servidor. Tente novamente."),
}


PAGE_MESSAGES = {
    404: "Página não encontrada.",
    405: "Ação não permitida nesta página.",
}


def error_response(status: int, code: str | None = None, message: str | None = None, fields: dict | None = None):
    default_code, default_message = MESSAGES.get(status, MESSAGES[500])
    body = {"error": {"code": code or default_code, "message": message or default_message}}
    if fields:
        body["error"]["fields"] = fields  # mensagem por campo do formulário
    return jsonify(body), status


def _respond(status: int):
    if request.path.startswith("/api/"):
        return error_response(status)
    message = PAGE_MESSAGES.get(status) or MESSAGES.get(status, MESSAGES[500])[1]
    page = {"endpoint": None, "title": f"Erro {status}", "summary": None}
    return render_template("error.html", page=page, status=status, message=message), status


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return error_response(exc.status, exc.code, exc.message, exc.fields)

    @app.errorhandler(HTTPException)
    def handle_http(exc: HTTPException):
        return _respond(exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # O detalhe vai para o log; o navegador recebe só a mensagem genérica.
        logger.exception("Erro não tratado: %s", exc)
        return _respond(500)
