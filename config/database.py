"""Ponto ÚNICO de acesso ao banco de dados (hoje SQLite).

Tudo que depende do motor SQL deve passar por aqui, para que uma futura
troca (ex.: PostgreSQL) mexa em um arquivo e não na aplicação inteira:

  get_connection()      conexão configurada
  inserir()             INSERT que devolve o id gerado
  ErroDeIntegridade     exceção de violação de UNIQUE/FK
  sql_norm()            comparação sem acento/caixa dentro do SQL
  like_ci()             LIKE sem diferenciar maiúsculas
  agora_utc_str(), hoje_iso()   datas calculadas em Python (não em SQL)

Inventário completo das dependências de SQLite: docs/banco-de-dados.md.
Camadas: rotas → services → models (repositórios: único lugar com SQL) → aqui.
"""
import sqlite3
import os
import unicodedata
from datetime import date, datetime, timedelta, timezone

DIALECT = 'sqlite'

# Violação de UNIQUE/FK/CHECK. PostgreSQL: psycopg.errors.IntegrityError.
ErroDeIntegridade = sqlite3.IntegrityError

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
    (o LIKE do SQLite só ignora caixa em ASCII, não acentos)."""
    if texto is None:
        return None
    decomposto = unicodedata.normalize('NFD', str(texto))
    return ''.join(ch for ch in decomposto if unicodedata.category(ch) != 'Mn').lower()


def get_connection():
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Função Python exposta ao SQL como normalizar(coluna) — ver sql_norm().
    conn.create_function('normalizar', 1, normalizar, deterministic=True)
    return conn


# ── Helpers que isolam diferenças entre motores SQL ─────────────────────

def inserir(cursor, sql, params=()):
    """Executa um INSERT e devolve o id gerado.
    SQLite: cursor.lastrowid. PostgreSQL: acrescentar 'RETURNING id' e ler
    a linha devolvida (psycopg não tem lastrowid)."""
    cursor.execute(sql, params)
    return cursor.lastrowid


def sql_norm(coluna):
    """Expressão SQL 'coluna sem acento e em minúsculas'.
    SQLite: função Python registrada acima. PostgreSQL: unaccent(lower(col))
    (extensão unaccent) ou coluna normalizada persistida."""
    return f"normalizar({coluna})"


def like_ci(coluna):
    """Condição 'coluna LIKE ?' sem diferenciar maiúsculas de minúsculas.
    SQLite: LIKE já ignora caixa (ASCII). PostgreSQL: usar ILIKE."""
    return f"{coluna} LIKE ?"


def agora_utc_str(dias_atras=0):
    """'YYYY-MM-DD HH:MM:SS' em UTC (mesmo formato de CURRENT_TIMESTAMP),
    para comparar com colunas created_at/updated_at sem funções de data do SQL."""
    return (datetime.now(timezone.utc) - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M:%S')


def hoje_iso():
    """Data de hoje 'YYYY-MM-DD' (para comparar com colunas de data em ISO)."""
    return date.today().isoformat()
