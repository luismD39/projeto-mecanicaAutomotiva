"""Catálogo de códigos DTC: carga inicial (seed), busca e detalhe.

O conteúdo fica em app/data/fault_codes.json para ser revisado sem mexer no código.
"""

import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.services.errors import NotFoundError, ValidationError

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "fault_codes.json"
REQUIRED_TEXT = ("code", "description", "system", "explanation")
REQUIRED_LISTS = ("causes", "symptoms", "checks")
QUERY_MAX = 50

# Ressalva exibida junto de todo código (CLAUDE.md, regra 10).
NOTE = (
    "O código direciona a investigação, mas não confirma sozinho qual peça está defeituosa. "
    "A interpretação, as causas prováveis e os procedimentos variam conforme veículo, motor e fabricante."
)


def load_catalog(path: Path = CATALOG_PATH) -> list[dict]:
    """Lê e valida o JSON. Um erro aqui impede o servidor de subir com dados incompletos."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    for entry in entries:
        for key in REQUIRED_TEXT:
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f"Código {entry.get('code')!r}: campo '{key}' ausente ou vazio")
        for key in REQUIRED_LISTS:
            items = entry.get(key)
            if not isinstance(items, list) or not items or not all(isinstance(i, str) and i for i in items):
                raise ValueError(f"Código {entry['code']}: '{key}' deve ser uma lista de textos")
    return entries


def seed(db: sqlite3.Connection) -> int:
    """Insere ou atualiza os códigos do catálogo. Pode rodar várias vezes sem duplicar."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = load_catalog()
    with db:
        for e in entries:
            db.execute(
                """
                INSERT INTO fault_codes (code, description, system, explanation,
                                         causes_json, symptoms_json, checks_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET
                    description = excluded.description, system = excluded.system,
                    explanation = excluded.explanation, causes_json = excluded.causes_json,
                    symptoms_json = excluded.symptoms_json, checks_json = excluded.checks_json
                """,
                (e["code"], e["description"], e["system"], e["explanation"],
                 json.dumps(e["causes"], ensure_ascii=False), json.dumps(e["symptoms"], ensure_ascii=False),
                 json.dumps(e["checks"], ensure_ascii=False), now),
            )
    return len(entries)


def _normalize(text: str) -> str:
    """Minúsculas e sem acentos, para 'combustao' encontrar 'combustão'."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _to_dict(row: sqlite3.Row) -> dict:
    return {
        "code": row["code"],
        "description": row["description"],
        "system": row["system"],
        "explanation": row["explanation"],
        "causes": json.loads(row["causes_json"]),
        "symptoms": json.loads(row["symptoms_json"]),
        "checks": json.loads(row["checks_json"]),
        "note": NOTE,
    }


def search(db: sqlite3.Connection, query) -> list[dict]:
    """Busca por código ou por texto. Todas as palavras digitadas precisam aparecer."""
    if query is None:
        query = ""
    if not isinstance(query, str) or len(query) > QUERY_MAX:
        raise ValidationError(f"A busca deve ter no máximo {QUERY_MAX} caracteres.", fields={"q": "Busca muito longa."})
    terms = _normalize(query).split()
    results = []
    # shortcut: filtra em Python (aceita busca sem acento); serve para dezenas de códigos, trocar por FTS5 se forem milhares.
    for row in db.execute("SELECT * FROM fault_codes ORDER BY code"):
        item = _to_dict(row)
        haystack = _normalize(" ".join([item["code"], item["description"], item["system"], item["explanation"],
                                        *item["causes"], *item["symptoms"]]))
        if all(term in haystack for term in terms):
            results.append({"code": item["code"], "description": item["description"], "system": item["system"]})
    return results


def get_fault_code(db: sqlite3.Connection, code: str) -> dict:
    row = db.execute("SELECT * FROM fault_codes WHERE code = ?", (code.strip().upper(),)).fetchone()
    if row is None:
        raise NotFoundError("Código não encontrado no catálogo.")
    return _to_dict(row)
