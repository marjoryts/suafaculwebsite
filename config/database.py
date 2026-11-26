"""Ponto ÚNICO de acesso ao banco de dados: PostgreSQL (Supabase).

Tudo que depende do motor SQL passa por aqui:

  get_connection()      conexão do pool (devolvida ao pool em close())
  inserir()             INSERT que devolve o id gerado (RETURNING id)
  ErroDeIntegridade     exceção de violação de UNIQUE/FK/CHECK
  sql_norm()            comparação sem acento/caixa dentro do SQL
  like_ci()             LIKE sem diferenciar maiúsculas (ILIKE)
  data_iso_sql()        texto 'AAAA-MM-DD' -> DATE (NULL se inválido)
  agora_utc_str(), hoje_iso()   datas calculadas em Python

Configuração (variáveis de ambiente):
  DATABASE_URL   string de conexão PostgreSQL. No Supabase use o pooler em
                 modo *transaction* (porta 6543) com o papel `suafacul_backend`
                 — ver docs/migracao-supabase.md. Obrigatória.
  DB_POOL_MAX    conexões no pool por processo (padrão 5).

Compatibilidade com o código dos models (escrito para o sqlite3):
  * placeholders `?` e `:nome` são traduzidos para `%s` / `%(nome)s`;
  * as linhas aceitam `linha['coluna']`, `linha[0]`, `dict(linha)` e
    desempacotamento, como o sqlite3.Row;
  * TIMESTAMPTZ volta como texto 'AAAA-MM-DD HH:MM:SS' em UTC e DATE como
    'AAAA-MM-DD' — o mesmo formato que a aplicação, os templates e a API
    sempre usaram (o contrato JSON não muda).
Camadas: rotas → services → models (repositórios: único lugar com SQL) → aqui.
"""
import atexit
import os
import re
import threading
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool

DIALECT = 'postgresql'

# Violação de UNIQUE/FK/CHECK.
ErroDeIntegridade = psycopg.errors.IntegrityError


def normalizar(texto):
    """Minúsculas e sem acentos: 'São Paulo' -> 'sao paulo'. Mesma regra da
    função SQL public.normalizar() (unaccent + lower), usada nas buscas para
    que 'sao', 'SÃO' e 'São' encontrem o mesmo registro."""
    if texto is None:
        return None
    decomposto = unicodedata.normalize('NFD', str(texto))
    return ''.join(ch for ch in decomposto if unicodedata.category(ch) != 'Mn').lower()


# ── Configuração e pool ─────────────────────────────────────────────────

def database_url():
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL não definida. Configure a string de conexão do Supabase "
            "(pooler, porta 6543, papel suafacul_backend) — ver .env.example e "
            "docs/migracao-supabase.md.")
    return url


def descrever_destino():
    """'host:porta/banco (usuário)' — para logs, SEM a senha."""
    try:
        partes = urlsplit(database_url())
        return f"{partes.hostname}:{partes.port or 5432}{partes.path} ({partes.username})"
    except Exception:
        return '(DATABASE_URL inválida)'


_pool = None
_pool_url = None
_pool_pid = None
_pool_trava = threading.Lock()


def _obter_pool():
    """Um pool por processo (recriado após fork e se a DATABASE_URL mudar).

    prepare_threshold=None: o pooler do Supabase em modo transaction não
    suporta prepared statements no servidor. check_connection descarta
    conexões que o pooler/serverless já tenha fechado antes de entregá-las.
    """
    global _pool, _pool_url, _pool_pid
    url = database_url()
    if _pool is not None and _pool_url == url and _pool_pid == os.getpid():
        return _pool
    with _pool_trava:
        if _pool is not None and _pool_url == url and _pool_pid == os.getpid():
            return _pool
        antigo = _pool if _pool_pid == os.getpid() else None
        _pool = ConnectionPool(
            url,
            min_size=0,
            max_size=max(1, int(os.environ.get('DB_POOL_MAX', '5') or 5)),
            max_idle=60,
            timeout=15,
            kwargs={'prepare_threshold': None, 'connect_timeout': 10},
            check=ConnectionPool.check_connection,
            open=True,
            name='suafacul',
        )
        _pool_url, _pool_pid = url, os.getpid()
    if antigo is not None:
        antigo.close()
    return _pool


def fechar_pool():
    """Fecha o pool do processo (testes, fim de comandos de CLI)."""
    global _pool, _pool_url, _pool_pid
    with _pool_trava:
        if _pool is not None and _pool_pid == os.getpid():
            _pool.close()
        _pool = _pool_url = _pool_pid = None


atexit.register(fechar_pool)


# ── Tradução de SQL e conversão de valores ──────────────────────────────

_TOKENS = re.compile(r"'(?:[^']|'')*'|::|\?|:[A-Za-z_]\w*|%")


@lru_cache(maxsize=2048)
def _traduzir(sql):
    """`?` -> %s, `:nome` -> %(nome)s, `%` literal -> %%. Literais entre
    aspas simples são preservados (só o `%` dentro deles é escapado)."""
    def trocar(m):
        t = m.group(0)
        if t.startswith("'"):
            return t.replace('%', '%%')
        if t == '::':
            return t
        if t == '?':
            return '%s'
        if t == '%':
            return '%%'
        return f'%({t[1:]})s'
    return _TOKENS.sub(trocar, sql)


def _parametros(params):
    if params is None:
        return ()
    if isinstance(params, dict):
        return params
    return tuple(params)


def _converter(valor):
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(timezone.utc)
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    return valor


class Linha:
    """Linha de resultado com o comportamento do sqlite3.Row."""
    __slots__ = ('_valores', '_indice')

    def __init__(self, valores, indice):
        self._valores = valores
        self._indice = indice

    def keys(self):
        return list(self._indice)

    def __getitem__(self, chave):
        if isinstance(chave, str):
            return self._valores[self._indice[chave]]
        return self._valores[chave]

    def __iter__(self):
        return iter(self._valores)

    def __len__(self):
        return len(self._valores)

    def __eq__(self, outro):
        if isinstance(outro, Linha):
            return self._valores == outro._valores
        return tuple(self._valores) == outro

    __hash__ = None

    def __repr__(self):
        return f"Linha({dict(zip(self._indice, self._valores))})"


def _fabrica_de_linhas(cursor):
    if cursor.description is None:
        return None
    indice = {}
    for i, coluna in enumerate(cursor.description):
        indice.setdefault(coluna.name, i)  # nome repetido: vale o primeiro (como no sqlite3)

    def fazer(valores):
        return Linha(tuple(_converter(v) for v in valores), indice)
    return fazer


class Cursor:
    def __init__(self, bruto):
        self._c = bruto

    def execute(self, sql, params=None):
        self._c.execute(_traduzir(sql), _parametros(params))
        return self

    def executemany(self, sql, sequencia):
        self._c.executemany(_traduzir(sql), [_parametros(p) for p in sequencia])
        return self

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    def __iter__(self):
        return iter(self._c.fetchall())

    @property
    def rowcount(self):
        return self._c.rowcount

    @property
    def description(self):
        return self._c.description

    def close(self):
        self._c.close()


class Conexao:
    """Conexão emprestada do pool. close() a devolve (o pool desfaz qualquer
    transação pendente). Se o chamador esquecer de fechar (ex.: um `return`
    dentro de um try sem finally), __del__ devolve a conexão mesmo assim."""

    def __init__(self, bruta, pool):
        self._bruta = bruta
        self._pool = pool

    def cursor(self):
        if self._bruta is None:
            raise psycopg.InterfaceError('Conexão já fechada.')
        return Cursor(self._bruta.cursor(row_factory=_fabrica_de_linhas))

    def execute(self, sql, params=None):
        return self.cursor().execute(sql, params)

    def executar_script(self, sql):
        """Vários comandos de uma vez (arquivos de migration). Sem parâmetros."""
        self._bruta.execute(sql)

    def commit(self):
        self._bruta.commit()

    def rollback(self):
        self._bruta.rollback()

    def close(self):
        bruta, self._bruta = self._bruta, None
        if bruta is None:
            return
        if self._pool is not None:
            try:
                # Leituras deixam uma transação aberta: encerra antes de devolver
                # (o pool faria o mesmo, mas registrando um aviso a cada leitura).
                if bruta.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                    bruta.rollback()
                self._pool.putconn(bruta)
            except Exception:
                bruta.close()
        else:
            bruta.close()

    def __enter__(self):
        return self

    def __exit__(self, tipo, *_):
        if self._bruta is not None:
            (self.rollback if tipo else self.commit)()
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def get_connection():
    pool = _obter_pool()
    return Conexao(pool.getconn(), pool)


def conexao_direta(url):
    """Conexão fora do pool (scripts de migração e testes)."""
    return Conexao(psycopg.connect(url, prepare_threshold=None, connect_timeout=10), None)


# ── Helpers que isolam detalhes do SQL ──────────────────────────────────

def inserir(cursor, sql, params=()):
    """Executa um INSERT e devolve o id gerado."""
    cursor.execute(sql.rstrip().rstrip(';') + ' RETURNING id', params)
    linha = cursor.fetchone()
    return linha[0] if linha else None


def sql_norm(coluna):
    """Expressão SQL 'coluna sem acento e em minúsculas' (public.normalizar,
    definida na migration e indexável por trigram)."""
    return f"public.normalizar({coluna})"


def padrao_contem(texto):
    """Padrão LIKE 'contém' já normalizado (sem acento/minúsculas) e com os
    curingas % e _ escapados — usar com `sql_norm(col) LIKE ? ESCAPE '\\'`."""
    texto = normalizar((texto or '').strip()).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f"%{texto}%"


def contem_sem_acento(coluna):
    """Condição 'coluna contém o termo', sem diferenciar acentos nem caixa."""
    return f"{sql_norm(coluna)} LIKE ? ESCAPE '\\'"


def like_ci(coluna):
    """Condição 'coluna LIKE ?' sem diferenciar maiúsculas de minúsculas."""
    return f"{coluna} ILIKE ?"


def data_iso_sql(coluna):
    """Texto 'AAAA-MM-DD' -> DATE; NULL quando não é uma data válida."""
    return f"public.data_iso({coluna})"


def agora_utc_str(dias_atras=0):
    """'YYYY-MM-DD HH:MM:SS' em UTC, para comparar com colunas TIMESTAMPTZ."""
    return (datetime.now(timezone.utc) - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M:%S')


def hoje_iso():
    """Data de hoje 'YYYY-MM-DD' (para comparar com colunas de data em ISO)."""
    return date.today().isoformat()
