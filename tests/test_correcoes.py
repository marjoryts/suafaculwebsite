"""Testes das correções de dados, segurança e conteúdo:
tipo de instituição dos cursos, senha do admin criado automaticamente,
escape de HTML nos cards e aviso no lugar do alert()."""
import os
import re
import sqlite3
import importlib

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ler(caminho):
    with open(os.path.join(RAIZ, caminho), encoding='utf-8') as f:
        return f.read()


# ── Tipo de instituição dos cursos ──

def test_cursos_de_universidades_publicas_nao_sao_privada(client):
    dados = client.get('/api/cursos/listar?tipo_instituicao=Privada&limit=100').get_json()
    instituicoes = {c['instituicao'] for c in dados['cursos']}
    for publica in ('USP', 'UFBA', 'UFF', 'UNIFESP'):
        assert not any(i.startswith(publica + ' ') for i in instituicoes), publica


def test_tipo_do_curso_igual_ao_da_faculdade_vinculada(app):
    from config.database import get_connection
    conn = get_connection()
    divergentes = conn.execute("""
        SELECT c.nome FROM cursos c JOIN faculdades f ON f.id = c.faculdade_id
         WHERE c.tipo_instituicao <> f.tipo_instituicao
    """).fetchall()
    conn.close()
    assert divergentes == []


def test_migracao_corrige_banco_antigo(app, monkeypatch):
    """Banco semeado com a lista antiga (curso público marcado Privada)
    é corrigido no próximo start."""
    from config.database import get_connection
    conn = get_connection()
    conn.execute("UPDATE cursos SET tipo_instituicao='Privada' WHERE nome='Direito' AND instituicao LIKE 'USP %'")
    conn.commit()
    conn.close()

    import database.init_db as init_db
    importlib.reload(init_db).init_db()

    conn = get_connection()
    tipo = conn.execute("SELECT tipo_instituicao FROM cursos WHERE nome='Direito' AND instituicao LIKE 'USP %'").fetchone()[0]
    conn.close()
    assert tipo == 'Pública'


# ── Senha do admin criado automaticamente ──

@pytest.mark.parametrize('ambiente, senha_ok, senha_bloqueada', [
    ({}, 'admin123', None),
    ({'VERCEL': '1'}, None, 'admin123'),
    ({'VERCEL': '1', 'SUAFACUL_ADMIN_PASSWORD': 'Senha-Forte-123'}, 'Senha-Forte-123', 'admin123'),
])
def test_senha_do_admin_inicial(tmp_path, monkeypatch, ambiente, senha_ok, senha_bloqueada):
    from werkzeug.security import check_password_hash
    db = tmp_path / 'admin.db'
    monkeypatch.setenv('SUAFACUL_DB_PATH', str(db))
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.delenv('SUAFACUL_ADMIN_PASSWORD', raising=False)
    for chave, valor in ambiente.items():
        monkeypatch.setenv(chave, valor)

    import database.init_db as init_db
    importlib.reload(init_db).init_db()

    hash_senha = sqlite3.connect(db).execute(
        "SELECT senha FROM usuarios WHERE nome_usuario='admin'").fetchone()[0]
    if senha_ok:
        assert check_password_hash(hash_senha, senha_ok)
    if senha_bloqueada:
        assert not check_password_hash(hash_senha, senha_bloqueada)


# ── Front-end ──

def test_scripts_nao_usam_alert_nos_favoritos():
    # chamada com argumento; comentários que citam alert() não contam
    assert not re.search(r'\balert\(\s*[^)\s]', _ler('public/js/favoritos.js'))


@pytest.mark.parametrize('arquivo', [
    'public/js/cursos.js',
    'public/js/faculdades.js',
    'public/js/home-cursos.js',
    'public/js/favoritos-page.js',
])
def test_cards_escapam_dados_da_api(arquivo):
    """Nenhum campo de curso/faculdade entra cru no HTML do card:
    toda interpolação ${course.x} / ${f.x} / ${itemData.x} que gera texto
    passa por escaparHtml() ou urlSegura()."""
    js = _ler(arquivo)
    crus = re.findall(r'\$\{(?:course|f|itemData)\.[a-z_]+\}', js)
    assert crus == [], f'{arquivo}: dados sem escape: {crus}'


def test_inicial_nao_promete_comparacao(client):
    html = client.get('/').get_data(as_text=True)
    assert 'compare as opções' not in html


def test_pasta_css_antiga_removida():
    assert not os.path.exists(os.path.join(RAIZ, 'public', 'pages'))
