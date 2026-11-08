"""Etapa 1: create_app() sem efeitos colaterais e paridade de rotas."""
import os
import subprocess
import sys

from conftest import PROJECT_ROOT, build_app

ROTAS_ESPERADAS = {
    # páginas
    ('/', 'GET'), ('/home', 'GET'), ('/login', 'GET'), ('/cursos', 'GET'), ('/faculdades', 'GET'),
    ('/vestibulares', 'GET'), ('/testevocacional', 'GET'), ('/sobrenos', 'GET'), ('/ajuda', 'GET'),
    ('/favoritos', 'GET'), ('/dashboard', 'GET'), ('/admin', 'GET'), ('/logout', 'GET'),
    ('/auth/google', 'GET'), ('/auth/google/callback', 'GET'),
    # API legada usada pelo frontend Web
    ('/api/usuario/registrar', 'POST'), ('/api/usuario/login', 'POST'),
    ('/api/usuario/logout', 'GET'), ('/api/usuario/logout', 'POST'),
    ('/api/usuario/listar', 'GET'), ('/api/usuario/buscar', 'GET'), ('/api/usuario/atualizar', 'POST'),
    ('/api/usuario/perfil', 'POST'), ('/api/usuario/definir-tipo', 'POST'), ('/api/usuario/deletar', 'POST'),
    ('/api/cursos/listar', 'GET'), ('/api/cursos/buscar', 'GET'), ('/api/cursos/sugestoes', 'GET'),
    ('/api/cursos/criar', 'POST'), ('/api/cursos/censo/importar-csv', 'POST'), ('/api/busca/sugestoes', 'GET'),
    ('/api/faculdades/listar', 'GET'), ('/api/faculdades/buscar', 'GET'), ('/api/faculdades/criar', 'POST'),
    ('/api/faculdades/atualizar', 'POST'), ('/api/faculdades/deletar', 'POST'),
    ('/api/faculdades/emec/importar', 'POST'), ('/api/faculdades/emec/importar-uf', 'POST'),
    ('/api/faculdades/emec/importar-csv', 'POST'), ('/api/faculdades/emec/importar-brasil', 'POST'),
    ('/api/vestibulares/listar', 'GET'), ('/api/vestibulares/buscar', 'GET'),
    ('/api/vestibulares/criar', 'POST'), ('/api/vestibulares/validar', 'GET'), ('/api/vestibulares/validar', 'POST'),
    ('/api/admin/stats', 'GET'),
    ('/api/favoritos/adicionar', 'POST'), ('/api/favoritos/remover', 'POST'), ('/api/favoritos/listar', 'GET'),
    ('/api/favoritos/verificar', 'GET'), ('/api/favoritos/listar-ids', 'GET'),
    ('/api/teste_vocacional/salvar', 'POST'),
    # API v1
    ('/api/v1/instituicoes', 'GET'), ('/api/v1/instituicoes/<codigo_emec>', 'GET'),
    ('/api/v1/instituicoes/<codigo_emec>/cursos', 'GET'),
}


def test_todas_as_rotas_existentes_foram_preservadas(app):
    """Nenhuma URL/método pode sumir na migração para blueprints."""
    atuais = {(r.rule, m) for r in app.app.url_map.iter_rules() if r.endpoint != 'static'
              for m in r.methods - {'HEAD', 'OPTIONS'}}
    assert ROTAS_ESPERADAS <= atuais, sorted(ROTAS_ESPERADAS - atuais)


def test_create_app_nao_toca_no_banco_nem_inicia_threads(monkeypatch, tmp_path):
    db = tmp_path / "nao_deve_existir.db"
    monkeypatch.setenv("SUAFACUL_DB_PATH", str(db))
    ns = build_app(monkeypatch, inicializar_banco=False)
    assert ns.app is not None
    assert not db.exists()
    assert not hasattr(ns, 'scheduler_service')  # sem agendador em processo (Vercel Cron)


def test_importar_wsgi_nao_tem_efeitos_colaterais(tmp_path):
    """O entrypoint da Vercel (wsgi.py) pode ser importado sem escrever em
    disco e sem iniciar threads — pré-requisito de execução serverless."""
    db = tmp_path / "wsgi_nao_deve_existir.db"
    env = {**os.environ, "SUAFACUL_DB_PATH": str(db), "FLASK_SECRET_KEY": "x" * 32,
           "FLASK_DEBUG": "0", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}
    codigo = ("import wsgi, threading; "
              "assert wsgi.app.name; "
              "assert threading.active_count() == 1; "
              "print('ok')")
    r = subprocess.run([sys.executable, "-c", codigo], cwd=PROJECT_ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'ok' in r.stdout
    assert not db.exists()


def test_configuracao_vem_do_ambiente_e_aceita_override(app):
    from app.factory import create_app
    outra = create_app(config={'TESTING': True, 'SESSION_COOKIE_SAMESITE': 'Strict'}, load_env=False)
    assert outra.config['SESSION_COOKIE_SAMESITE'] == 'Strict'
    assert outra is not app.app
