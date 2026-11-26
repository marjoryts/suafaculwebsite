"""Fixtures compartilhadas dos testes.

Os testes rodam contra um PostgreSQL REAL (o mesmo motor do Supabase), nunca
contra o banco de produção: cada teste recebe um banco novo, clonado de um
template que já tem as migrations de supabase/migrations/ aplicadas.

Configure TEST_DATABASE_URL com um usuário que possa criar bancos, ex.:
    TEST_DATABASE_URL=postgresql://postgres:senha@localhost:5432/postgres
(pode ser o Postgres local do `supabase start`). Sem ela, os testes que usam
banco são pulados.

Para rodar a APLICAÇÃO com o papel restrito de produção (`suafacul_backend`,
sujeito a RLS e sem DDL) defina também TEST_DATABASE_APP_USER e
TEST_DATABASE_APP_PASSWORD (o papel precisa ter LOGIN no servidor de teste).
O esquema e a migração de dados continuam usando o usuário administrador.
"""
import itertools
import os
import sys
import uuid
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

_PREFIXO = f"suafacul_t{uuid.uuid4().hex[:6]}"
_TEMPLATE = f"{_PREFIXO}_template"
_contador = itertools.count()


def _url_servidor():
    url = os.environ.get('TEST_DATABASE_URL', '').strip()
    if not url:
        pytest.skip('TEST_DATABASE_URL não definida (PostgreSQL de testes).')
    return url


def _url_do_banco(nome, como_app=False):
    partes = urlsplit(_url_servidor())
    usuario = os.environ.get('TEST_DATABASE_APP_USER', '').strip()
    if como_app and usuario:
        host = partes.hostname + (f':{partes.port}' if partes.port else '')
        senha = os.environ.get('TEST_DATABASE_APP_PASSWORD', '')
        partes = partes._replace(netloc=f'{usuario}:{senha}@{host}')
    return urlunsplit(partes._replace(path='/' + nome))


def _admin(sql):
    import psycopg
    with psycopg.connect(_url_servidor(), autocommit=True) as conn:
        conn.execute(sql)


@pytest.fixture(scope='session')
def _template_pg():
    """Banco template com o esquema (migrations) aplicado e nenhum dado."""
    _url_servidor()
    from config.database import conexao_direta, fechar_pool
    from database.init_db import aplicar_migracoes
    _admin(f'DROP DATABASE IF EXISTS "{_TEMPLATE}"')
    _admin(f'CREATE DATABASE "{_TEMPLATE}"')
    _admin(f"ALTER DATABASE \"{_TEMPLATE}\" SET timezone TO 'UTC'")
    conn = conexao_direta(_url_do_banco(_TEMPLATE))
    aplicar_migracoes(conn)
    conn.commit()
    conn.close()
    yield _TEMPLATE
    fechar_pool()
    _admin(f'DROP DATABASE IF EXISTS "{_TEMPLATE}" WITH (FORCE)')


@pytest.fixture()
def novo_banco(_template_pg, monkeypatch):
    """Cria um banco vazio (só esquema) e aponta DATABASE_URL (a conexão da
    aplicação) para ele. Devolve a URL de ADMINISTRADOR do banco (usada por
    quem precisa de DDL, como a migração de dados). Chamar de novo cria outro."""
    criados = []

    def criar():
        nome = f"{_PREFIXO}_{next(_contador)}"
        _admin(f'CREATE DATABASE "{nome}" TEMPLATE "{_template_pg}"')
        criados.append(nome)
        monkeypatch.setenv('DATABASE_URL', _url_do_banco(nome, como_app=True))
        monkeypatch.delenv('DATABASE_URL_ADMIN', raising=False)
        return _url_do_banco(nome)

    yield criar
    from config.database import fechar_pool
    fechar_pool()
    for nome in criados:
        _admin(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def build_app(monkeypatch, inicializar_banco=True):
    """Cria o app via factory, isolado do ambiente do desenvolvedor.

    A factory chama load_dotenv() (que NÃO sobrescreve variáveis já presentes
    no ambiente, nem as vazias), então definir as variáveis aqui — mesmo como
    string vazia — impede que o .env real vaze para os testes.

    Devolve um namespace com o app Flask (`.app`) e os módulos/models que os
    testes usam, mantendo a interface do antigo `import app.py`.
    """
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")  # test client fala HTTP
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setenv("SUAFACUL_ADMIN_PASSWORD", "admin123")  # só nos testes
    monkeypatch.setenv("SUAFACUL_ADMIN_USER", "")
    monkeypatch.setenv("SUAFACUL_ADMIN_EMAIL", "")

    from app.factory import create_app
    from app.bootstrap import init_database
    from app.models.curso import Curso
    from app.models.faculdade import Faculdade
    from app.models.favorito import Favorito
    from app.models.teste_vocacional import TesteVocacional
    from app.models.usuario import Usuario
    from app.models.vestibular import Vestibular
    from app.services import (busca_service, censo_service, emec_service, oauth_service,
                              automacao_service, seed_service, vestibular_service, vocacional_service)
    from app.security import destino_seguro
    from database.init_db import init_db

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    if inicializar_banco:
        init_database(flask_app)

    return SimpleNamespace(
        app=flask_app, init_db=init_db,
        Curso=Curso, Faculdade=Faculdade, Favorito=Favorito, TesteVocacional=TesteVocacional,
        Usuario=Usuario, Vestibular=Vestibular,
        busca_service=busca_service, censo_service=censo_service, emec_service=emec_service,
        oauth_service=oauth_service, automacao_service=automacao_service,
        seed_service=seed_service, vestibular_service=vestibular_service,
        vocacional_service=vocacional_service, _destino_seguro=destino_seguro,
    )


@pytest.fixture()
def app(novo_banco, monkeypatch):
    # get_connection() lê DATABASE_URL a cada chamada (e recria o pool quando
    # ela muda), então cada teste usa só o próprio banco.
    novo_banco()
    return build_app(monkeypatch)


@pytest.fixture()
def client(app):
    return app.app.test_client()


@pytest.fixture()
def admin_client(client):
    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    return client
