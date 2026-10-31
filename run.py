"""Inicia o servidor local: python run.py  (outra porta: defina a variável PORT)"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Só escuta no próprio computador (127.0.0.1); não expõe na rede.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
