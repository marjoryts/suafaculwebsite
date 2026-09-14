"""Fixtures compartilhadas dos testes. Usa um banco SQLite temporário
(nunca o banco de desenvolvimento) para cada sessão de testes."""
import os
import sys
import tempfile
import importlib.util

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test_suafacul.db"

    # get_connection() resolve o caminho do banco via variável de ambiente
    # a cada chamada (ver config/database.py), então isso isola o banco de
    # cada teste mesmo com o cache de módulos do Python entre testes.
    monkeypatch.setenv("SUAFACUL_DB_PATH", str(db_path))
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    spec = importlib.util.spec_from_file_location("suafacul_app_under_test", os.path.join(PROJECT_ROOT, "app.py"))
    appmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(appmod)
    appmod.app.config.update(TESTING=True)
    yield appmod


@pytest.fixture()
def client(app):
    return app.app.test_client()


@pytest.fixture()
def admin_client(client):
    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    return client
