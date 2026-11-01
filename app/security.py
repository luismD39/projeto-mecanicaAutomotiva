"""Proteções básicas (servidor local e publicação de testes no Render)."""

from urllib.parse import urlparse

from flask import abort, request

WRITE_METHODS = {"POST", "PUT", "DELETE"}


def register_security(app) -> None:
    @app.before_request
    def block_cross_site_writes():
        # Outro site aberto no mesmo navegador poderia enviar POST para 127.0.0.1 (CSRF).
        # O navegador informa a origem; só aceitamos ações vindas das páginas do próprio AutoScan Pro.
        # Compara só o endereço (host:porta): no Render o navegador usa https, mas o Flask recebe http do proxy.
        origin = request.headers.get("Origin")
        if request.method in WRITE_METHODS and origin and urlparse(origin).netloc != request.host:
            abort(403)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
