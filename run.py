"""Inicia o servidor local.

Desenvolvimento:  python run.py                (modo debug, porta 5000 ou a variável PORT)
Apresentação:     iniciar.bat, que define AUTOSCAN_APRESENTACAO=1:
                  sem modo debug, procura uma porta livre e abre o navegador sozinho.
"""

import os
import socket
import threading
import webbrowser

from app import create_app

HOST = "127.0.0.1"  # só escuta no próprio computador; não expõe na rede

app = create_app()


def free_port(start: int, attempts: int = 20) -> int:
    """Primeira porta livre a partir de `start` (a 5000 pode estar ocupada no computador da escola)."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:
                return port
    raise SystemExit(f"Nenhuma porta livre entre {start} e {start + attempts - 1}. Feche outros programas e tente de novo.")


if __name__ == "__main__":
    presentation = os.environ.get("AUTOSCAN_APRESENTACAO") == "1"
    port = int(os.environ.get("PORT", 5000))
    if presentation:
        port = free_port(port)
        url = f"http://{HOST}:{port}"
        print(f"\n  AutoScan Pro rodando em {url}\n  Para encerrar, feche esta janela.\n")
        threading.Timer(1.5, webbrowser.open, args=[url]).start()
    app.run(host=HOST, port=port, debug=not presentation)
