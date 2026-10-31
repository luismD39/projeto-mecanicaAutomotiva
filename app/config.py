"""Configuração central da aplicação."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "AutoScan Pro"
APP_VERSION = "1.0.0-dev"


class Config:
    DATABASE = str(BASE_DIR / "instance" / "autoscan.db")
    TESTING = False
