"""Gera o pacote portátil para Windows: dist/AutoScanPro.zip

Uso (precisa de internet SÓ aqui, para baixar as bibliotecas):
    .venv\\Scripts\\python empacotar.py

O pacote leva as bibliotecas já baixadas (pasta wheels) para Python 3.11 a 3.14 em
Windows 64 bits. No computador da apresentação, o iniciar.bat instala tudo sem internet.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
OUT = DIST / "AutoScanPro"
PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    print("Copiando o programa...")
    shutil.copytree(ROOT / "app", OUT / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("run.py", "requirements.txt", "README.md"):
        shutil.copy2(ROOT / name, OUT / name)
    shutil.copy2(ROOT / "pacote" / "LEIA-ME.txt", OUT / "LEIA-ME.txt")
    # O cmd do Windows exige quebras de linha CRLF nos .bat.
    bat = (ROOT / "pacote" / "iniciar.bat").read_text(encoding="utf-8").replace("\r\n", "\n")
    (OUT / "iniciar.bat").write_bytes(bat.replace("\n", "\r\n").encode("utf-8"))

    for version in PYTHON_VERSIONS:
        print(f"Baixando bibliotecas para Python {version} (Windows 64 bits)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "-r", str(ROOT / "requirements.txt"),
             "-d", str(OUT / "wheels"), "--only-binary=:all:", "--platform", "win_amd64",
             "--python-version", version, "--disable-pip-version-check", "-q"],
            check=True,
        )

    archive = shutil.make_archive(str(DIST / "AutoScanPro"), "zip", DIST, "AutoScanPro")
    size_mb = Path(archive).stat().st_size / 1_000_000
    print(f"\nPacote pronto: {archive} ({size_mb:.1f} MB)")
    print("Copie o .zip para o pendrive, extraia no computador da apresentação e abra iniciar.bat.")


if __name__ == "__main__":
    main()
