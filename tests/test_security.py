"""Testes da Etapa 0 (correções de segurança críticas) — ver docs/seguranca-etapa0.md."""
from types import SimpleNamespace

import pytest

from config.database import get_connection


def _importar_app(monkeypatch, tmp_path, **env):
    """Cria o app via factory com um ambiente controlado e inicializa o banco.
    Valores '' (em vez de ausentes) impedem que o load_dotenv() traga o .env
    real do desenvolvedor."""
    base = {
        "SUAFACUL_DB_PATH": str(tmp_path / "sec.db"),
        "FLASK_SECRET_KEY": "x" * 32,
        "FLASK_DEBUG": "0",
        "SESSION_COOKIE_SECURE": "",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "SUAFACUL_ADMIN_PASSWORD": "",
    }
    base.update(env)
    for chave, valor in base.items():
        if valor is None:
            monkeypatch.delenv(chave, raising=False)
        else:
            monkeypatch.setenv(chave, valor)
    from app.bootstrap import init_database
    from app.factory import create_app
    flask_app = create_app()
    init_database(flask_app)
    return SimpleNamespace(app=flask_app)


# ── Configuração insegura ───────────────────────────────────────────────

def test_debug_desligado_quando_flask_debug_nao_definido(monkeypatch, tmp_path):
    mod = _importar_app(monkeypatch, tmp_path, FLASK_DEBUG=None)
    assert mod.app.config['DEBUG'] is False


def test_sem_secret_key_fora_do_debug_nao_sobe(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        _importar_app(monkeypatch, tmp_path, FLASK_SECRET_KEY="")


def test_chave_legada_publica_e_rejeitada(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError):
        _importar_app(monkeypatch, tmp_path, FLASK_SECRET_KEY="suafacul_secret_key_change_in_production")


def test_sem_secret_key_em_debug_usa_chave_efemera(monkeypatch, tmp_path):
    mod = _importar_app(monkeypatch, tmp_path, FLASK_SECRET_KEY="", FLASK_DEBUG="1")
    assert mod.app.secret_key and mod.app.secret_key != "suafacul_secret_key_change_in_production"


def test_cookie_secure_por_padrao_fora_do_debug(monkeypatch, tmp_path):
    mod = _importar_app(monkeypatch, tmp_path)
    assert mod.app.config['SESSION_COOKIE_SECURE'] is True
    assert mod.app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert mod.app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_cookie_de_sessao_emitido_com_httponly_e_samesite(client):
    r = client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    cookie = r.headers.get('Set-Cookie', '')
    assert 'HttpOnly' in cookie
    assert 'SameSite=Lax' in cookie


# ── Credenciais administrativas padrão ──────────────────────────────────

def test_banco_novo_sem_senha_de_bootstrap_nao_tem_admin_padrao(monkeypatch, tmp_path):
    mod = _importar_app(monkeypatch, tmp_path)
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    conn.close()
    assert total == 0
    r = mod.app.test_client().post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    assert r.get_json()['success'] is False


def test_bootstrap_cria_admin_somente_com_senha_explicita(monkeypatch, tmp_path):
    mod = _importar_app(monkeypatch, tmp_path, SUAFACUL_ADMIN_PASSWORD="senha-forte-9",
                        SUAFACUL_ADMIN_USER="root")
    r = mod.app.test_client().post('/api/usuario/login', data={'username': 'root', 'password': 'senha-forte-9'})
    assert r.get_json()['success'] is True


def test_primeiro_usuario_registrado_nao_vira_admin(app, client):
    conn = get_connection()
    conn.execute("DELETE FROM usuarios")
    conn.commit()
    conn.close()
    client.post('/api/usuario/registrar', data={'username': 'ana', 'email': 'ana@x.com', 'password': 'segredo1'})
    app.init_db()  # simula novo boot / cold start
    conn = get_connection()
    tipo = conn.execute("SELECT tipo FROM usuarios WHERE nome_usuario='ana'").fetchone()[0]
    conn.close()
    assert tipo == 'aluno'


# ── Autorização / autenticação ──────────────────────────────────────────

def test_admin_rebaixado_perde_acesso_imediatamente(admin_client):
    assert admin_client.get('/api/admin/stats').status_code == 200
    conn = get_connection()
    conn.execute("UPDATE usuarios SET tipo='aluno' WHERE nome_usuario='admin'")
    conn.commit()
    conn.close()
    assert admin_client.get('/api/admin/stats').status_code == 403


def test_usuario_excluido_perde_sessao_admin(admin_client):
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE nome_usuario='admin'")
    conn.commit()
    conn.close()
    assert admin_client.get('/api/admin/stats').status_code == 401


def test_login_nao_revela_se_usuario_existe(client):
    inexistente = client.post('/api/usuario/login', data={'username': 'ninguem', 'password': 'qualquer1'}).get_json()
    senha_errada = client.post('/api/usuario/login', data={'username': 'admin', 'password': 'errada123'}).get_json()
    assert inexistente['success'] is False and senha_errada['success'] is False
    assert inexistente['message'] == senha_errada['message']


def test_registro_exige_senha_minima(client):
    r = client.post('/api/usuario/registrar', data={'username': 'bob', 'email': 'bob@x.com', 'password': '123'})
    assert r.get_json()['success'] is False
