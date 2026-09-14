import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'suafacul.db')


def _resolve_db_path():
    # Permite que os testes apontem para um banco temporário sem precisar
    # recarregar módulos já importados (ver tests/conftest.py).
    return os.environ.get('SUAFACUL_DB_PATH', DB_PATH)


def get_connection():
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
