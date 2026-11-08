"""Fixtures compartilhadas dos testes. Usa um banco SQLite temporário
(nunca o banco de desenvolvimento) para cada teste."""
import os
import sys
from types import SimpleNamespace

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


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
    # E-mails vão para uma caixa de saída em memória (nada é enviado de verdade).
    monkeypatch.setenv("EMAIL_MODO", "memoria")
    for var in ("SMTP_HOST", "SMTP_USUARIO", "SMTP_SENHA", "GOOGLE_ANDROID_CLIENT_ID", "GOOGLE_IOS_CLIENT_ID"):
        monkeypatch.setenv(var, "")
    from app.services import email_service
    email_service.caixa_de_saida.clear()

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
def app(tmp_path, monkeypatch):
    # get_connection() resolve o caminho do banco via variável de ambiente
    # a cada chamada (ver config/database.py), então isso isola o banco de
    # cada teste mesmo com o cache de módulos do Python entre testes.
    monkeypatch.setenv("SUAFACUL_DB_PATH", str(tmp_path / "test_suafacul.db"))
    return build_app(monkeypatch)


@pytest.fixture()
def client(app):
    return app.app.test_client()


@pytest.fixture()
def admin_client(client):
    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    return client
