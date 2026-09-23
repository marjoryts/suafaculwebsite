import sqlite3
import os
import unicodedata

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'suafacul.db')


def _resolve_db_path():
    # Permite que os testes apontem para um banco temporário sem precisar
    # recarregar módulos já importados (ver tests/conftest.py).
    return os.environ.get('SUAFACUL_DB_PATH', DB_PATH)


def normalizar(texto):
    """Minúsculas e sem acentos: 'São Paulo' -> 'sao paulo'. Usada nas
    buscas para que 'sao', 'SÃO' e 'São' encontrem o mesmo registro
    (o LIKE/NOCASE do SQLite só ignora caixa em ASCII, não acentos)."""
    if texto is None:
        return None
    decomposto = unicodedata.normalize('NFD', str(texto))
    return ''.join(ch for ch in decomposto if unicodedata.category(ch) != 'Mn').lower()


def get_connection():
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Disponível no SQL como normalizar(coluna) — ver busca_service.py.
    conn.create_function('normalizar', 1, normalizar, deterministic=True)
    return conn
