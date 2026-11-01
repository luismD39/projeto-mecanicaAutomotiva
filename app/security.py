"""Proteções básicas para um servidor local."""

from flask import abort, request

WRITE_METHODS = {"POST", "PUT", "DELETE"}


def register_security(app) -> None:
    @app.before_request
    def block_cross_site_writes():
        # Outro site aberto no mesmo navegador poderia enviar POST para 127.0.0.1 (CSRF).
        # O navegador informa a origem; só aceitamos ações vindas das páginas do próprio AutoScan Pro.
        origin = request.headers.get("Origin")
        if request.method in WRITE_METHODS and origin and origin != request.host_url.rstrip("/"):
            abort(403)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
