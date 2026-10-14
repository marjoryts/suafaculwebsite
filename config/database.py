import sqlite3
import os
import unicodedata

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'suafacul.db')


# Na Vercel (e em qualquer serverless), o diretório do código (/var/task) é
# SOMENTE LEITURA — o único lugar gravável é /tmp. Sem isso o
# sqlite3.connect() em database/suafacul.db falha com "unable to open
# database file" já no import do app, e TODA rota responde 500.
# A Vercel define VERCEL=1 automaticamente em build e runtime.
VERCEL_DB_PATH = '/tmp/suafacul.db'


def _resolve_db_path():
    # Ordem: SUAFACUL_DB_PATH (testes ou caminho explícito) > /tmp na
    # Vercel > database/suafacul.db (desenvolvimento local).
    caminho = os.environ.get('SUAFACUL_DB_PATH', '').strip()
    if caminho:
        return caminho
    if os.environ.get('VERCEL'):
        return VERCEL_DB_PATH
    return DB_PATH


def get_db_path():
    """Caminho efetivo do banco no ambiente atual."""
    return _resolve_db_path()


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
